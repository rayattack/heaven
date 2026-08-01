from asyncio import gather, get_running_loop, sleep as asleep
from collections import deque
from functools import wraps
from http import HTTPStatus
from importlib import import_module
from inspect import isclass, iscoroutinefunction
from os import path, getcwd
from typing import Any, Callable, Tuple, Union, overload, TypeVar, Generic

T = TypeVar("T")

import mimetypes
from pytastic import Pytastic
from pytastic.exceptions import ValidationError
from aiofiles import open as async_open_file
import time
import asyncio
import logging
from jinja2 import Environment, FileSystemLoader, PrefixLoader, ChoiceLoader, select_autoescape
from uvicorn import run
from orjson import dumps, loads

from .constants import (
    CONNECT,
    DEFAULT,
    DELETE,
    GET,
    HEAD,
    METHODS,
    METHOD_CONNECT,
    METHOD_DELETE,
    METHOD_GET,
    METHOD_HEAD,
    METHOD_OPTIONS,
    METHOD_PATCH,
    METHOD_POST,
    METHOD_PUT,
    METHOD_TRACE,
    METHOD_WEBSOCKET,
    OPTIONS,
    PATCH,
    POST,
    PUT,
    SHUTDOWN,
    SOCKET,
    STARTUP,
    STATUS_NOT_FOUND as NOT_FOUND,
    TRACE,
    URL_ERROR_MESSAGE,
    WILDCARD
)
from .utils import CONVERTERS, parameter_parts, preprocessor
from .request import Request
from .response import Response
from .context import Context, Look, Key
from .handler import Handler as RequestHandler
from .errors import AbortException, HandlerError, ParameterError, SubdomainError, UrlDuplicateError, UrlError

methods = ['get', 'post', 'put', 'delete', 'connect', 'head', 'options', 'patch']

Handles = Callable[[Request, Response, Context], object]
Handler = Union[Handles, str]

SEPARATOR = INDEX = "/"


def _closure_mounted_application(handler: Handles, mounted: 'Router'):
    async def delegate(req: Request, res: Response, ctx: Context):
        req.mounted = mounted
        res._mounted_from_application = mounted
        if iscoroutinefunction(handler): await handler(req, res, ctx)
        else: handler(req, res, ctx)
    return delegate


def _closure_mounted_ws(handler: Handles, mounted: 'Router'):
    async def delegate(sender, receiver, req: Request, ctx):
        req.mounted = mounted
        if iscoroutinefunction(handler): await handler(sender, receiver, req, ctx)
        else: handler(sender, receiver, req, ctx)
    return delegate


def _get_configuration(configurator=None):
    if not configurator: return {}
    if isinstance(configurator, dict): return configurator
    return configurator()


def _isparamx(r: str):
    return (':', r[1:],) if r.startswith(':') else (r, None,)


def _notify(width=80, event=STARTUP): #pragma: nocover
    drawline = lambda: print('=' * width)
    drawline()
    print(f'NOTE: The `LAST` {event} func above failed and prevented others from running')
    drawline()


def _set_content_type(req: Request, res: Response):
    mime_type, _ = mimetypes.guess_type(req.url)
    if mime_type:
        res.headers = 'Content-Type', mime_type


class _Probe(object):
    """Stand-in for a Request when walking the tree purely to ask whether a path
    would match. Route.match writes params/qh as it goes; here they are discarded."""
    params = None
    qh = None


OPENAPI_TYPES = {
    'bool': {'type': 'boolean'},
    'date': {'type': 'string', 'format': 'date'},
    'datetime': {'type': 'string', 'format': 'date-time'},
    'float': {'type': 'number'},
    'int': {'type': 'integer'},
    'str': {'type': 'string'},
    'uuid': {'type': 'string', 'format': 'uuid'},
}


def _openapi_path(route: str) -> Tuple[str, list]:
    """Translate heaven's `/users/:id` route syntax into OpenAPI's `/users/{id}`,
    returning the rewritten path alongside its path-parameter definitions."""
    parameters = []
    segments = []
    for segment in route.split('?', 1)[0].split(SEPARATOR):
        if not segment.startswith(':'):
            segments.append(segment)
            continue
        name, kind = parameter_parts(segment[1:])
        segments.append(f'{{{name}}}')
        parameters.append({
            'name': name,
            'in': 'path',
            'required': True,
            'schema': dict(OPENAPI_TYPES.get(kind, {'type': 'string'})),
        })
    return SEPARATOR.join(segments), parameters


def _class_to_function_handler(spec: str):
    """Resolve `'package.module.Class#method'` into a callable of the usual
    `(req, res, ctx)` shape. Everything that can be checked is checked here, at
    registration, so a broken handler fails at boot rather than on a request."""
    target, _, name = spec.partition('#')
    if '.' not in target:
        raise HandlerError(f'"{spec}" needs the module path to its class, as in "package.module.Class#{name or "method"}"')
    if not name:
        raise HandlerError(f'"{spec}" names no method - write it as "{target}#method"')

    module_name, class_name = target.rsplit('.', 1)
    module = import_module(module_name)
    try: klass = getattr(module, class_name)
    except AttributeError: raise HandlerError(f'"{module_name}" has no class "{class_name}" for handler "{spec}"')

    if not isclass(klass) or not issubclass(klass, RequestHandler):
        raise HandlerError(f'"{target}" must be a subclass of heaven.Handler to be registered as "{spec}"')

    method = getattr(klass, name, None)
    if method is None:
        raise HandlerError(f'"{class_name}" has no method "{name}" for handler "{spec}"')
    if not callable(method):
        raise HandlerError(f'"{spec}" is not callable - "{name}" is an attribute of "{class_name}", not a method')

    # One instance per request, so `self` is request scoped. Binding the trio onto
    # a single shared instance would let two requests in flight overwrite each
    # other's `self.res` the moment either awaits.
    if iscoroutinefunction(method):
        async def delegate(req: Request, res: Response, ctx: Context):
            return await getattr(klass(req, res, ctx), name)()
    else:
        def delegate(req: Request, res: Response, ctx: Context):
            return getattr(klass(req, res, ctx), name)()

    # __wrapped__ points tooling at the method the user actually wrote, so
    # `heaven routes` reports their file rather than this module
    delegate.__name__ = f'{class_name}#{name}'
    delegate.__qualname__ = delegate.__name__
    delegate.__doc__ = method.__doc__
    delegate.__wrapped__ = method
    return delegate


def _string_to_function_handler(handler: Handler):
    if isinstance(handler, str) and '#' in handler:
        return _class_to_function_handler(handler)
    if isinstance(handler, str) and '.' in handler:
        module_name, function_name = handler.rsplit('.', 1)
        module = import_module(module_name)
        handler = getattr(module, function_name)
    return handler


class Parameter(object):
    def __init__(self, value: Any, potentials: dict[str, str]):
        '''Potentials are a dictionary of potential parameter names'''
        self._value = value
        self._potentials = potentials

    def resolve(self, parameter_address: str) -> Tuple[str, Any]:
        param = self._potentials.get(parameter_address)
        if not param: raise ParameterError(f'no parameter registered for {parameter_address}')

        key, kind = parameter_parts(param)
        if not kind: return key, self._value

        # the type name was checked when the route was registered, so it is present
        try: return key, CONVERTERS[kind](self._value)
        except Exception: raise ParameterError(f'{self._value!r} is not a valid {kind}')



class Route(object):
    def __init__(self, route: str, handler: Callable, router: 'Router') -> None:
        self.heaven_instance = router
        self.parameterized = {}
        self.queryhint = None
        self.route = route
        self.handler = handler
        self.children = {}

    def match(self, routes: deque, r: Request) -> Tuple[str, Callable[[Request, Response, Context], None]]:
        matched: str = ''
        node: Route = self
        route_at_deviation = '/'.join(routes)
        parameters = []

        # grand father deviation point in case
        # we are dealing from the start with a catch all route
        deviation_point: Union[Route, None] = node.children.get('*')

        while routes:
            route = routes.popleft()
            current_node = node.children.get(route)
            if not current_node:
                # is there a parameterized child?
                current_node = node.children.get(':')
                if current_node:
                    # we are going to use this later when we know the address that has been matched
                    parameters.append(Parameter(value = route, potentials = current_node.parameterized))

                    if(node.children.get('*')):
                        """If there was also a wildcard seeing as placeholder ':' takes precedence, then
                        mark the point it deviated so it is possible to backtrack and use that point for
                        matching if this path fumbles later"""
                        route_at_deviation = '/'.join([route, *routes])
                        deviation_point = node.children.get('*')

                    node = current_node
                    continue

                # you get here if no ':' above and at that point return what you find 
                wildcard = node.children.get('*')
                if wildcard:  #pragma: nocover
                    r.params = '*', '/'.join([route, *routes])
                    return wildcard.route, wildcard.handler

                # did we find a deviation point beside a ':' earlier or maybe grand parent?
                # then return that
                if deviation_point:
                    r.params = '*', route_at_deviation
                    return deviation_point.route, deviation_point.handler
                
                # no current node and no wildcard or ':' so return '' and not found
                return matched, self.not_found

            # move to the next
            node = current_node

        # if we encountered a node along the way skip this block
        # was there a wildcard encountered along the way
        # this can be the grand parent * or the one encountered after ':' if any
        if deviation_point and not node.route:
            r.params = '*', route_at_deviation
            return deviation_point.route, deviation_point.handler

        # the url ran out on an interior node i.e. it is a strict prefix of a
        # registered route. Such a node carries no route/handler/queryhint, so
        # treat it as a miss rather than reading None off it below.
        if not node.route: return matched, self.not_found

        # time to process what parameters we saw. A typed segment that cannot read
        # its value means this route does not describe the url after all, so treat
        # it as a miss rather than handing the handler an unconverted string.
        try:
            for parameter in parameters: r.params = parameter.resolve(node.route)
        except ParameterError:
            # back out to a wildcard we passed on the way here, the same way a
            # structural miss does, and drop any params resolved before the failure
            if deviation_point:
                r._params = None
                r.params = '*', route_at_deviation
                return deviation_point.route, deviation_point.handler
            return matched, self.not_found
        r.qh = node.queryhint
        return node.route, node.handler

    def not_found(self, r: Request, w: Response, c: Context):
        w.status = 404
        w.body = b'Not found'


class Routes(object):
    def __init__(self):
        self.afters = {}
        self.befores = {}

        # Method scoping lives here, keyed by (route pattern, handler), so that
        # registering one function twice with different scopes keeps them apart
        # instead of stamping the scope onto the shared function object.
        self.aftermethods = {}
        self.beforemethods = {}

        self.cache = {CONNECT: {}, DELETE: {}, GET: {}, HEAD: {}, OPTIONS: {}, PATCH: {}, POST: {}, PUT: {}, TRACE: {}, SOCKET: {}}
        self.routes = {}

        # (method, route) pairs whose body is handed to the handler in chunks
        # instead of being buffered before it runs
        self.streams = set()

    def add(self, method: str, route: str, handler: Callable, router: 'Router', stream=False):
        """
        method: one of POST, GET, OPTIONS... etc - i.e. the HTTP method
        route: the route url/endpoint
        handler: function corresponding to the signature of a heaven handler
        stream: leave the body unread so the handler can consume it with req.stream()
        """
        queryhint = ''
        if len(route.split('?')) > 1:
            route, queryhint = route.split('?', 1)

        if stream: self.streams.add((method, route))

        # ensure the method and route combo has not been already registered
        try: assert self.cache.get(method, {}).get(route) is None
        except AssertionError: raise UrlDuplicateError(f'URL: {route} already registered for METHOD: {method}')

        self.cache[method][route] = handler

        # here we check and set the root to be a route node i.e. / with no handler
        # if necessary so we can traverse freely
        route_node: Route = self.routes.get(method)
        if not route_node:
            route_node = Route(route = None, handler = None, router = router)
            self.routes[method] = route_node

        if route == SEPARATOR:
            route_node.route = route
            route_node.handler = handler
            route_node.queryhint = queryhint
            return

        # Otherwise strip and split the routes into stops or stoppable
        # stumps i.e. /customers/:id/orders -> [customers, :id, orders]
        routes = route.strip(SEPARATOR).split(SEPARATOR)

        # get the length of the routes so we can use for validation checks in a loop later
        stop_at = len(routes) - 1

        for index, part in enumerate(routes):
            # this gives us ':' and the remainder i.e. xxx if heaven is of the form :xxx
            # otherwise it will return heaven if heaven is any other str
            label, remainder = _isparamx(part)
            if remainder:
                name, kind = parameter_parts(remainder)
                if not name:
                    raise UrlError(f'Route parameter ":{remainder}" in {route} has no name')
                if kind and kind not in CONVERTERS:
                    raise UrlError(
                        f'Unknown type "{kind}" for route parameter ":{remainder}" in {route}. '
                        f'Valid types are: {", ".join(sorted(CONVERTERS))}'
                    )

            new_route_node = route_node.children.get(label)
            if not new_route_node:
                new_route_node = Route(None, None, router)
                route_node.children[label] = new_route_node

            route_node = new_route_node
            if remainder: route_node.parameterized[route] = remainder

            if index == stop_at:
                assert route_node.handler is None, f'Handler already registered for route: {route}'
                route_node.route = route
                route_node.handler = handler
                route_node.queryhint = queryhint

    @property
    def after(self):
        raise KeyError('Not readable')

    @after.setter
    def after(self, pair):
        route, handler = pair
        routes = self.afters.get(route)
        if routes:
            routes.append(handler)
        else:
            self.afters[route] = [handler]

    @property
    def before(self):
        raise KeyError('Not readable')

    @before.setter
    def before(self, values):
        route, handler = values
        routes = self.befores.get(route)
        if routes:
            routes.append(handler)
        else:
            self.befores[route] = [handler]

    def _scope(self, store, route, handler, methods):
        """Record which HTTP methods this (route, handler) registration answers to.
        An unscoped registration means every method, and wins over a narrower one
        registered for the same pair."""
        key = (route, handler)
        if not methods:
            store[key] = None
            return
        scope = frozenset(m.upper() for m in methods)
        existing = store.get(key, scope)
        store[key] = None if existing is None else (existing | scope)

    def add_before(self, route, handler, methods=None):
        self._scope(self.beforemethods, route, handler, methods)
        routes = self.befores.get(route)
        if routes:
            routes.append(handler)
        else:
            self.befores[route] = [handler]

    def add_after(self, route, handler, methods=None):
        self._scope(self.aftermethods, route, handler, methods)
        routes = self.afters.get(route)
        if routes:
            routes.append(handler)
        else:
            self.afters[route] = [handler]

    def get_handler(self, routes):
        for route in routes:...
        return None, None

    def resolve(self, method: str, route: str, r):
        """Walk the tree registered for `method` and return the matched route, its
        handler, and the tree root. All three are None when nothing matches."""
        if not self.cache.get(method): return None, None, None

        route_node: Route = self.routes.get(method)
        if not route_node: return None, None, None

        if route == SEPARATOR:
            return route_node.route, route_node.handler, route_node

        matched, handler = route_node.match(deque(route.strip(SEPARATOR).split('/')), r)
        return matched, handler, route_node

    def allowed(self, route: str):
        """The HTTP methods that have a handler registered for this path."""
        allowed = set()
        for method, route_node in self.routes.items():
            if method == SOCKET or not route_node: continue
            if route == SEPARATOR:
                if route_node.handler: allowed.add(method)
                continue
            matched, _ = route_node.match(deque(route.strip(SEPARATOR).split('/')), _Probe())
            if matched: allowed.add(method)
        # anything answering GET answers HEAD too
        if GET in allowed: allowed.add(HEAD)
        return allowed

    def unmatched(self, scope, method: str, route: str, w: Response):
        """Nothing is registered for this method+path. If the path exists under a
        different method that is a 405 with an Allow header, otherwise a 404."""
        if scope['type'] != 'http': return w

        allowed = self.allowed(route)
        allowed.discard(method)
        if not allowed: return w

        w.status = 405
        w.headers = 'Allow', ', '.join(sorted(allowed))
        w.body = b'Method not allowed'
        return w

    async def buffer(self, r: Request, receive, w: Response, application):
        """Read the whole request body onto the Request. Returns False when it goes
        past the app's `max_body_size`, leaving a 413 on the response and stopping
        the read rather than accumulating the rest of it."""
        limit = getattr(application, '_max_body_size', None)

        chunks = []
        size = 0
        oversized = False
        more = True
        while more:
            message = await receive()
            chunk = message.get('body', b'')
            more = message.get('more_body', False)

            # Past the limit we keep reading but stop keeping, so memory holds at the
            # ceiling while the client still gets to finish sending and read the 413.
            # Responding mid-upload instead resets the connection and the client sees
            # a broken pipe rather than the reason it was refused.
            if oversized: continue

            size += len(chunk)
            if limit is not None and size > limit:
                oversized = True
                chunks = []
                continue

            chunks.append(chunk)

        if oversized:
            w.status = 413
            w.body = b'Payload too large'
            return False

        # joined once. Repeatedly concatenating onto a bytes object copies everything
        # accumulated so far on each of the hundreds of chunks a server sends, which
        # is quadratic in the size of the upload.
        r._body = b''.join(chunks)
        return True

    async def handle(self, scope, receive, send, metadata=None, application=None):
        """
        Traverse internal route tree and use appropriate method
        """
        method = scope.get('method')
        if scope['type'] == 'websocket': method = SOCKET

        r = Request(scope, b'', receive, metadata, application)
        c = Context(application)
        w = Response(context=c, app=application, request=r)

        route = scope.get('path')
        matched, handler, route_node = self.resolve(method, route, r)

        # HEAD is a GET without a body, so let a plain GET route answer it rather
        # than requiring the same handler to be registered twice.
        if not matched and method == HEAD:
            matched, handler, route_node = self.resolve(GET, route, r)

        # Resolving first means a body is only read once we know somewhere wants it,
        # so an unmatched url no longer buffers whatever was sent with it.
        if not matched: return self.unmatched(scope, method, route, w)

        if scope['type'] == 'http':
            if (method, matched) in self.streams: r._streaming = True
            elif not await self.buffer(r, receive, w, application): return w

        r._application = route_node.heaven_instance
        r._route = matched

        # call all pre handle request hooks but first reset response_writer from not found to found
        w.status = 200; w.body = b''
        try:
            await self.xhooks(self.befores, self.beforemethods, matched, r, w, c, before=True)

            # call request handler
            if w._abort: raise AbortException
            try: handler.__requesthandler__
            except: pass
            else: handler = handler.__call__
            if method == SOCKET:
                await send({'type': 'websocket.accept'})
                async def sender(data):
                    msg = {'type': 'websocket.send'}
                    if isinstance(data, str): msg['text'] = data
                    else: msg['bytes'] = data
                    await send(msg)

                async def receiver():
                    while True:
                        msg = await receive()
                        if msg['type'] == 'websocket.disconnect': return None
                        if msg['type'] == 'websocket.receive':
                            return msg.get('text') or msg.get('bytes')

                if iscoroutinefunction(handler): await handler(sender, receiver, r, c)
                else: handler(sender, receiver, r, c)
            else:
                if iscoroutinefunction(handler): await handler(r, w, c)
                else: handler(r, w, c)

            # call all post handle request hooks
            await self.xhooks(self.afters, self.aftermethods, matched, r, w, c)
        except AbortException:
            return w
        except Exception as e:
            # Preserve response w (which carries BEFORE hook headers like CORS)
            # and attach the exception so __call__ can log/debug it.
            w._unhandled_error = e
            w.status = 500
            w.body = b"Internal Server Error"

        return w

    def remove(self, method: str, route: str):
        assert method in METHODS
        route_node = self.routes.get(method)
        if not route_node: return
        if not route_node.children: return

        routes = route.strip(SEPARATOR).split(SEPARATOR)
        stop_at = len(routes) - 1
        for index, heaven in enumerate(routes):
            _heaven, _parameterized = _isparamx(heaven)
            route_node = route_node.children.get(_heaven)
            if not route_node:
                return
            if index == stop_at:
                route_node.route = None
                route_node.handler = None
                self.cache[method][route] = None

    async def xhooks(self, hookstore, methodstore, matched, r: Request, w: Response, c: Context, before=False):
        """Run the hooks registered for `matched`, outermost pattern first on the way
        in and innermost first on the way out, so BEFORE/AFTER pairs nest properly:

            BEFORE:  /*  ->  /users/*  ->  /users/:id  ->  handler
            AFTER:                         /users/:id  ->  /users/*  ->  /*
        """
        parts = matched.strip(SEPARATOR).split(SEPARATOR)
        wildcards = []
        for position, part in enumerate(parts):
            joinedparts = "/".join(parts[:position])
            _ = '' if position == 0 else SEPARATOR
            # broadest first i.e. /*, then /users/*, then /users/:id/*
            wildcards.append(f'/{joinedparts}{_}*')

        if before: patterns = [*wildcards, matched]
        else: patterns = [matched, *reversed(wildcards)]

        # A hook registered under several matching patterns still runs only once,
        # at the earliest position it appears in.
        hooks = []
        seen = set()
        for pattern in patterns:
            for hook in hookstore.get(pattern, []):
                if hook in seen: continue
                seen.add(hook)
                hooks.append((pattern, hook))

        for pattern, hook in hooks:
            if w._abort: raise AbortException

            # Skip if this registration is method-scoped and the request doesn't match
            hook_methods = methodstore.get((pattern, hook))
            if hook_methods and r.method not in hook_methods:
                continue

            # Check for Earth bypasses
            application = r._application
            if application and hasattr(application, 'earth'):
                if hook in application.earth._bypasses:
                    continue
                # Also check unwrapped original if it exists
                original = getattr(hook, '__wrapped__', hook)
                if original in application.earth._bypasses:
                    continue

            if iscoroutinefunction(hook): await hook(r, w, c)
            else: hook(r, w, c)


class SchemaRegistry:
    def __init__(self, router: 'Router'):
        self._router = router
        self._schemas = {}

    def add(self, method: str, route: str, expects=None, returns=None, summary=None, description=None, protect=None, partial=None, strict=None, group=None, dot=False, subdomain=DEFAULT):
        self._schemas[(method.upper(), route, subdomain)] = {
            'expects': _string_to_function_handler(expects) if expects else None,
            'returns': _string_to_function_handler(returns) if returns else None,
            'summary': summary,
            'description': description,
            'protect': protect,
            'partial': partial,
            'strict': strict,
            'group': group,
            'dot': dot
        }

    def POST(self, route: str, **kwargs): self.add('POST', route, **kwargs)
    def GET(self, route: str, **kwargs): self.add('GET', route, **kwargs)
    def PUT(self, route: str, **kwargs): self.add('PUT', route, **kwargs)
    def DELETE(self, route: str, **kwargs): self.add('DELETE', route, **kwargs)
    def PATCH(self, route: str, **kwargs): self.add('PATCH', route, **kwargs)


class BoundSchemaRegistry:
    def __init__(self, registry: SchemaRegistry, subdomain: str):
        self.registry = registry
        self.subdomain = subdomain

    def POST(self, route: str, **kwargs): self.registry.add('POST', route, subdomain=self.subdomain, **kwargs)
    def GET(self, route: str, **kwargs): self.registry.add('GET', route, subdomain=self.subdomain, **kwargs)
    def PUT(self, route: str, **kwargs): self.registry.add('PUT', route, subdomain=self.subdomain, **kwargs)
    def DELETE(self, route: str, **kwargs): self.registry.add('DELETE', route, subdomain=self.subdomain, **kwargs)
    def PATCH(self, route: str, **kwargs): self.registry.add('PATCH', route, subdomain=self.subdomain, **kwargs)


class SubdomainContext:
    def __init__(self, app: 'Router', name: str):
        self.app = app
        self.name = name

    @property
    def schema(self):
        return BoundSchemaRegistry(self.app.schema, self.name)
    
    def AFTER(self, route: str, handler: Handler): self.app.AFTER(route, handler, subdomain=self.name)
    def BEFORE(self, route: str, handler: Handler): self.app.BEFORE(route, handler, subdomain=self.name)
    def CONNECT(self, route: str, handler: Handler): self.app.CONNECT(route, handler, subdomain=self.name)
    def DELETE(self, route: str, handler: Handler): self.app.DELETE(route, handler, subdomain=self.name)
    def GET(self, route: str, handler: Handler): self.app.GET(route, handler, subdomain=self.name)
    def HEAD(self, route: str, handler: Handler): self.app.HEAD(route, handler, subdomain=self.name)
    def HTTP(self, route: str, handler: Handler): self.app.HTTP(route, handler, subdomain=self.name)
    def OPTIONS(self, route: str, handler: Handler): self.app.OPTIONS(route, handler, subdomain=self.name)
    def PATCH(self, route: str, handler: Handler, stream=False): self.app.PATCH(route, handler, subdomain=self.name, stream=stream)
    def POST(self, route: str, handler: Handler, stream=False): self.app.POST(route, handler, subdomain=self.name, stream=stream)
    def PUT(self, route: str, handler: Handler, stream=False): self.app.PUT(route, handler, subdomain=self.name, stream=stream)
    def TRACE(self, route: str, handler: Handler): self.app.TRACE(route, handler, subdomain=self.name)
    def SOCKET(self, route: str, handler: Handler): self.app.SOCKET(route, handler, subdomain=self.name)
    def WEBSOCKET(self, route: str, handler: Handler): self.app.WEBSOCKET(route, handler, subdomain=self.name)
    def WS(self, route: str, handler: Handler): self.app.WS(route, handler, subdomain=self.name)
    def ASSETS(self, folder: str, route=None, relative_to=None): self.app.ASSETS(folder, route, subdomain=self.name, relative_to=relative_to)
    def abettor(self, method: str, route: str, handler: Handler): self.app.abettor(method, route, handler, subdomain=self.name)
    def doc(self, route: str, title="API Reference", version="0.0.1", favicon=None): self.app.DOCS(route, title, version, subdomain=self.name, favicon=favicon)
    def cors(self, handler=None, **kwargs): return self.app.cors(handler, subdomains=[self.name], **kwargs)


class Router(object):
    def __init__(self, configurator=None, protect_output=True, allow_partials=False, fail_on_output=True, debug=False, monitor: Union[float, None] = None, max_body_size: Union[int, None] = None):
        self._debug = debug
        self._max_body_size = max_body_size
        self.__ws = None
        self.finalized = False
        self.initializers = deque()
        self.deinitializers = deque()
        self.subdomains = {}
        self.subdomains[DEFAULT] = Routes()
        self._buckets = {}
        self._configuration = _get_configuration(configurator)
        self._templater = None
        self._loader = None
        self._template_prefix = None
        self.__daemons = []
        self.schema = SchemaRegistry(self)
        self._docs_config = None
        self._baked = False
        self._protect_output = protect_output
        self._allow_partials = allow_partials
        self._fail_on_output = fail_on_output
        
        if monitor and monitor > 0:
            logger = logging.getLogger("heaven.monitor")
            async def _watchdog(app):
                start = time.time()
                await asyncio.sleep(monitor)
                lag = time.time() - start - monitor
                if lag > monitor: logger.warning(f"Event Loop Blocked! Lag: {lag:.4f}s")
                return monitor
            self.__daemons.append(_watchdog)
        
        self._pytastic = Pytastic()


    @property
    def _(self):
        return Look(self._buckets)

    @property
    def earth(self):
        if not hasattr(self, '_earth'):
            from .earth import Earth
            self._earth = Earth(self)
        return self._earth

    def _bake_schemas(self):
        if self._baked: return
        for (method, route, subdomain), meta in self.schema._schemas.items():
            expects = meta.get('expects')
            if expects:
                is_patch = method.upper() == 'PATCH'
                dot = meta.get('dot', False)
                async def validate_hook(req, res, ctx, schema=expects, patch=is_patch, dot=dot):
                    try:
                        if patch:
                            req._data = self._pytastic.patch(schema, req.json, dot=dot)
                        else:
                            req._data = self._pytastic.validate(schema, req.json, dot=dot)
                    except ValidationError as e:
                        print(f"[HEAVEN 422] schema={schema}, error={e}, body={req.json}")
                        res.status = 422
                        res.body = str(e).encode()
                        res.abort(res.body)
                self.BEFORE(route, validate_hook, subdomain=subdomain, methods=[method])
            
            returns = meta.get('returns')
            if returns:
                protect = meta.get('protect')
                if protect is None: protect = self._protect_output
                
                partial = meta.get('partial')
                if partial is None: partial = self._allow_partials
                
                strict = meta.get('strict')
                if strict is None: strict = self._fail_on_output
                
                async def output_hook(req, res, ctx, schema=returns, protect=protect, partial=partial, strict=strict):
                    if res.body is None or res._abort: return
                    if isinstance(res.body, (bytes, str)) or hasattr(res.body, '__aiter__'): return

                    try:
                        if protect or partial:
                            res.body = self._pytastic.validate(schema, res.body, strip=protect, partial=partial)

                        res.headers = "Content-Type", "application/json"
                        res.body = dumps(res.body)
                    except Exception as e:
                        if strict:
                            res.status = 500
                            res.body = f"Output Validation Error: {str(e)}".encode()
                        else:
                            res.headers = "Content-Type", "application/json"
                            res.body = dumps(res.body)
                
                self.AFTER(route, output_hook, subdomain=subdomain, methods=[method])
        self._baked = True

    async def __call__(self, scope, receive, send):
        if scope['type'] == 'lifespan':
            while True:
                message = await receive()
                if message['type'] == 'lifespan.startup':
                    try: await self._register()
                    except: _notify()
                    await send({'type': 'lifespan.startup.complete'})
                    await self.__rundaemons()
                elif message['type'] == 'lifespan.shutdown':
                    try: await self._unregister()
                    except: _notify(event=SHUTDOWN)
                    await send({'type': 'lifespan.shutdown.complete'})

        metadata = preprocessor(scope)
        subdomain = metadata[0]
        wildcard_engine = self.subdomains.get(WILDCARD)
        engine: Union[Routes, None] = self.subdomains.get(subdomain)
        if not engine:
            engine = wildcard_engine if wildcard_engine else self.subdomains.get(DEFAULT)
        if not self._baked: self._bake_schemas()

        response = await engine.handle(scope, receive, send, metadata, self)  # type: ignore

        # If the handler raised an unhandled exception, log it and optionally
        # show Guardian Angel — but keep the same response object so BEFORE
        # hook headers (CORS, etc.) are preserved.
        err = getattr(response, '_unhandled_error', None)
        if err:
            import traceback
            print(f"[HEAVEN 500] {scope.get('method', '?')} {scope.get('path', '?')} — {err}")
            traceback.print_exc()
            if self._debug:
                from .response import _get_guardian_angel
                _get_guardian_angel(response, err)

        if isinstance(response.body, (dict, list)):
            try:
                response.body = dumps(response.body)
                # Ensure Content-Type is set to application/json if missing
                if not any(h[0].lower() == b'content-type' for h in response.headers):
                    response.header('Content-Type', 'application/json')
            except Exception as e:
                print(f"JSON Serialization Error: {e}")
                response.status = 500
                response.body = b"Internal Server Error: JSON Serialization Failed"
        
        # a HEAD response carries the headers a GET would, but never a body
        if scope.get('method') == HEAD: response.body = b''

        if scope['type'] == 'http':
            await send({'type': 'http.response.start', 'headers': response.headers, 'status': response.status})
            if hasattr(response.body, '__aiter__'):
                async for chunk in response.body:
                    await send({'type': 'http.response.body', 'body': chunk, 'more_body': True})
                await send({'type': 'http.response.body', 'body': b'', 'more_body': False})
            else:
                await send({'type': 'http.response.body', 'body': response.body, **response.metadata})

        # add background tasks
        if response.deferred:
            await gather(*[func(self) for func in response._deferred])

    async def __rundaemons(self):
        loop = get_running_loop()
        for daemon in self.__daemons:
            print(f'(X):  starting daemon: ', daemon.__name__)
            loop.create_task(daemon(self))

    async def _register(self):
        i = len(self.initializers)
        while self.initializers:
            initializer, c = self.initializers.popleft(), len(self.initializers)
            index = i - c
            print(f'({index}): ', initializer.__name__, '\n')
            if iscoroutinefunction(initializer): await initializer(self)
            else: initializer(self)

    async def _unregister(self):
        i = len(self.deinitializers)
        while self.deinitializers:
            deinitializer, c = self.deinitializers.popleft(), len(self.deinitializers)
            index = i - c
            print(f'({index}): ', deinitializer.__name__, '\n')
            if iscoroutinefunction(deinitializer): await deinitializer(self)
            else: deinitializer(self)

    def abettor(self, method: str, route: str, handler: Handler, subdomain=DEFAULT, router = None, stream=False):
        if not route.startswith('/'): raise UrlError(f'{route} is not a valid route - must start with /')
        handler = _string_to_function_handler(handler)
        engine = self.subdomains.get(subdomain)
        if not isinstance(engine, Routes):
            raise SubdomainError
        engine.add(method, route, handler, router or self, stream=stream)

    def call(self, handler: str, *args, **kwargs):
        if isinstance(handler, str): handler = _string_to_function_handler(handler)
        handler(self, *args, **kwargs)
        return self

    @property
    def daemons(self):
        return self.__daemons

    @daemons.setter
    def daemons(self, afunction):
        # Bind the daemon to the router it was registered on, the way ONCE already
        # does for lifecycle callbacks. A mounted child's daemon then still receives
        # the child, whose buckets and config an isolated mount does not share with
        # the parent that ends up running it.
        owner = self

        @wraps(afunction)
        async def _daemon(app=None):
            loop = get_running_loop()
            if (iscoroutinefunction(afunction)):
                sleeps = await afunction(owner)
            else:
                # Run sync functions in a thread pool to avoid blocking the event loop
                sleeps = await loop.run_in_executor(None, afunction, owner)

            if sleeps is None or sleeps == False: return
            await asleep(sleeps)
            loop.create_task(_daemon(app))
        self.__daemons.append(_daemon)

    @overload
    def keep(self, key: Key[T], value: T) -> None: ...
    
    @overload
    def keep(self, key: str, value: Any) -> None: ...

    def keep(self, key: Union[str, Key[T]], value: Any):
        if isinstance(key, Key):
            self._buckets[key.name] = value
        else:
            self._buckets[key] = value

    def unkeep(self, key: Union[str, Key[T]]):
        k = key.name if isinstance(key, Key) else key
        value = self._buckets[k]
        del self._buckets[k]
        return value

    @overload
    def peek(self, key: Key[T]) -> Union[T, None]: ...
    
    @overload
    def peek(self, key: str) -> Any: ...

    def peek(self, key: Union[str, Key[T]]) -> Any:
        k = key.name if isinstance(key, Key) else key
        try: value = self._buckets[k]
        except KeyError: return None
        else: return value


    def plugin(self, plugin_instance):
        """
        Registers a plugin with the application.
        The plugin instance must have an 'install' method which takes the app as the only argument.
        """
        if not hasattr(plugin_instance, 'install'):
            raise ValueError(f"Plugin {plugin_instance.__class__.__name__} must have an 'install' method")
        
        plugin_instance.install(self)
        return self

    def cors(self, handler=None, subdomains=None, **kwargs):
        """
        Enables Cross-Origin Resource Sharing (CORS) for the application.
        Accepts a handler function or configuration via kwargs.
        subdomains: list of subdomain names to apply CORS to (defaults to ["www"]).
        """
        _subdomains = subdomains or [DEFAULT]
        if isinstance(_subdomains, str): _subdomains = [_subdomains]

        handler = _string_to_function_handler(handler) if handler else None
        if handler and callable(handler):
            for sd in _subdomains:
                self.BEFORE("/*", handler, subdomain=sd)
                self.OPTIONS("/*", lambda req, res, ctx: None, subdomain=sd)
            return self

        # Smart key mapping
        def get_value(key, default=None):
            # Normalization helper: remove - and _ and lowercase
            normalize = lambda k: k.lower().replace('-', '').replace('_', '')
            target = normalize(key)
            
            # Additional semantic aliases
            aliases = {
                'origin': ['origins'],
                'methods': ['method', 'allowmethods', 'allowedmethods'],
                'headers': ['header', 'allowheaders', 'allowedheaders'],
                'exposeheaders': ['exposeheader', 'expose', 'allowedexposeheaders'],
                'credentials': ['allowcredentials', 'allowcreds', 'allowedcredentials'],
                'maxage': ['maxaage', 'maxage'],
            }
            
            targets = [target] + aliases.get(target, [])
            for k, v in kwargs.items():
                if normalize(k) in targets: return v
            return default

        origin_val = get_value('origin', '*')
        methods_val = get_value('methods', '*')
        headers_val = get_value('headers', '*')
        expose_val = get_value('expose_headers', '*')
        cred_val = get_value('credentials', False)
        max_age_val = get_value('max_age')

        async def handle_cors(req, res, ctx):
            allow_origin = origin_val
            if isinstance(origin_val, (list, tuple, set)):
                req_origin = req.headers.get("origin")
                if req_origin in origin_val:
                    allow_origin = req_origin
                    res.headers = "Vary", "Origin"
                else: allow_origin = "null"
            
            res.headers = "Access-Control-Allow-Origin", allow_origin
            if cred_val: res.headers = "Access-Control-Allow-Credentials", "true"
            if expose_val: res.headers = "Access-Control-Expose-Headers", expose_val
            
            if req.method == "OPTIONS":
                if max_age_val: res.headers = "Access-Control-Max-Age", max_age_val
                res.headers = "Access-Control-Allow-Methods", methods_val
                res.headers = "Access-Control-Allow-Headers", headers_val
                res.status = 200
                res.body = b""
                res.abort(b"")
            else:
                # Some clients require these on normal requests too
                res.headers = "Access-Control-Allow-Methods", methods_val
                res.headers = "Access-Control-Allow-Headers", headers_val

        for sd in _subdomains:
            self.BEFORE("/*", handle_cors, subdomain=sd)
            self.OPTIONS("/*", lambda req, res, ctx: None, subdomain=sd)
        return self

    def sessions(self, secret_key, cookie_name="session", max_age=3600, subdomains=None, **cookie_opts):
        """
        Enables secure, signed cookie-based sessions.
        subdomains: list of subdomain names to apply sessions to (defaults to ["www"]).
        """
        _subdomains = subdomains or [DEFAULT]
        if isinstance(_subdomains, str): _subdomains = [_subdomains]

        from .security import SecureSerializer
        serializer = SecureSerializer(secret_key)

        # Merge sensible defaults with caller overrides
        opts = dict(path="/", httponly=True, samesite="Lax")
        opts.update(cookie_opts)

        async def load_session(req, res, ctx):
            cookie = req.cookies.get(cookie_name)
            data = {}
            if cookie:
                try: data = serializer.loads(cookie, max_age=max_age)
                except: pass

            # attach to context and wrapping in Look so attributes can be accessed via dot notation
            # e.g. ctx.session.user_id
            ctx.keep('session', Look(data))
            # track initial state to avoid unnecessary writes
            ctx._initial_session = dumps(data)

        async def save_session(req, res, ctx):
            if not hasattr(ctx, 'session'): return

            # Check if session was modified
            # We access _data directly because ctx.session is a Look wrapper around the dict
            current_data = ctx.session._data if hasattr(ctx.session, '_data') else ctx.session
            try: current = dumps(current_data)
            except: return

            if current == getattr(ctx, '_initial_session', b''): return

            # Sign and Serialize
            token = serializer.dumps(current_data)

            # Set cookie via res.cookie which handles all directives
            res.cookie(cookie_name, token, max_age=max_age, **opts)

        for sd in _subdomains:
            self.BEFORE("/*", load_session, subdomain=sd)
            self.AFTER("/*", save_session, subdomain=sd)
        return self

    def listen(self, host='localhost', port: int = 8701, debug=None, **kwargs): #pragma: nocover
        # `debug` sets the app's own error-page mode; uvicorn dropped its debug
        # argument years ago so it is deliberately not forwarded.
        if debug is not None: self._debug = debug
        run(self, host=host, port=port, **kwargs)

    def subdomain(self, subdomain: str):
        if not self.subdomains.get(subdomain):
            self.subdomains[subdomain] = Routes()
        return SubdomainContext(self, subdomain)

    def mount(self, router: 'Router', isolated = True, prefer=None):
        # Absorb child pytastic registrations (custom getters/setters, validators, etc.)
        # onto the parent's instance. `prefer` resolves conflicts: None raises,
        # 'parent'/'self' keeps the parent's registration, 'child'/'incoming' keeps
        # the child's. Any other value is passed through to pytastic.Pytastic.use.
        _prefer = prefer
        if prefer in ('parent', 'self'): _prefer = self._pytastic
        elif prefer in ('child', 'incoming'): _prefer = router._pytastic
        if _prefer is None: self._pytastic.use(router._pytastic)
        else: self._pytastic.use(router._pytastic, prefer=_prefer)

        # Carry child schema registrations over so _bake_schemas (which only reads
        # self.schema._schemas on the parent) actually wires up validation hooks.
        for key, meta in router.schema._schemas.items():
            self.schema._schemas[key] = meta

        # Rebind so any further child.schema.*/child.vx.* registrations after mount
        # land on the shared instances and take effect.
        router._pytastic = self._pytastic
        router.schema = self.schema

        if not isolated:
            self._buckets = {**router._buckets, **self._buckets}
            self._configuration = {**router._configuration, **self._configuration}
            if self._loader and router._loader:
                if router._template_prefix or self._template_prefix:
                    # Build a combined loader that respects prefixes
                    prefixed = {}
                    unprefixed = []

                    # Collect from the child (mounted) router
                    if router._template_prefix:
                        prefixed[router._template_prefix] = router._loader
                    else:
                        unprefixed.append(router._loader)

                    # Collect from the parent router
                    current_loader = self._templater.loader if self._templater else None
                    if isinstance(current_loader, ChoiceLoader):
                        for sub in current_loader.loaders:
                            if isinstance(sub, PrefixLoader):
                                prefixed.update(sub.mapping)
                            else:
                                unprefixed.append(sub)
                    elif isinstance(current_loader, PrefixLoader):
                        prefixed.update(current_loader.mapping)
                    elif current_loader:
                        unprefixed.append(current_loader)

                    # Build the combined loader
                    loaders = []
                    if prefixed:
                        loaders.append(PrefixLoader(prefixed))
                    loaders.extend(unprefixed)

                    combined = ChoiceLoader(loaders) if len(loaders) > 1 else loaders[0]
                    self._templater.loader = combined
                else:
                    self._loader.searchpath = [*router._loader.searchpath, *self._loader.searchpath]

        self.deinitializers.extend(router.deinitializers)
        self.initializers.extend(router.initializers)

        # Daemons are bound to the child at registration, so the parent can start
        # them on its own lifespan without changing which app they see.
        self.__daemons.extend(router.__daemons)

        for subdomain in router.subdomains:
            engine: Routes = router.subdomains[subdomain]
            for method in engine.cache:
                cache = engine.cache[method]
                for route in cache:
                    handler = cache[route]
                    self.subdomain(subdomain)
                    if method == SOCKET:
                        closured_handler = _closure_mounted_ws(handler, router)
                    else:
                        closured_handler = _closure_mounted_application(handler, router)
                    self.abettor(method, route, closured_handler, subdomain=subdomain,
                                 router=router if isolated else self,
                                 stream=(method, route) in engine.streams)
            for after in engine.afters:
                self.subdomains[subdomain].afters[after] = [*engine.afters[after], *self.subdomains[subdomain].afters.get(after, [])]
            for before in engine.befores:
                # Parent hooks (self) come BEFORE Child hooks (engine) for .BEFORE
                self.subdomains[subdomain].befores[before] = [*self.subdomains[subdomain].befores.get(before, []), *engine.befores[before]]

            # carry the child's method scoping across; the parent's own registrations
            # win where both describe the same (route, handler) pair
            parent = self.subdomains[subdomain]
            parent.aftermethods = {**engine.aftermethods, **parent.aftermethods}
            parent.beforemethods = {**engine.beforemethods, **parent.beforemethods}

    def websocket(self):
        # only if app is already running
        if(self.__ws): return
        self.__ws = True

    @property
    def ws(self):
        return self.__ws

    def AFTER(self, route: str, handler: Handler, subdomain=DEFAULT, methods=None):
        if not route.startswith('/'): raise UrlError(URL_ERROR_MESSAGE)
        engine = self.subdomains.get(subdomain)
        if not isinstance(engine, Routes): #pragma: nocover
            raise NameError('Subdomain does not exist - register subdomain on router first')
        handler = _string_to_function_handler(handler)
        engine.add_after(route, handler, methods=methods)

    def BEFORE(self, route: str, handler: Handler, subdomain=DEFAULT, methods=None):
        if not route.startswith('/'): raise UrlError(URL_ERROR_MESSAGE)
        engine = self.subdomains.get(subdomain)
        if not isinstance(engine, Routes): #pragma: nocover
            raise NameError('Subdomain does not exist - register subdomain on router first')
        handler = _string_to_function_handler(handler)
        engine.add_before(route, handler, methods=methods)

    def CONNECT(self, route: str, handler: Handler, subdomain=DEFAULT):
        self.abettor(METHOD_CONNECT, route, handler, subdomain)

    def CONFIG(self, config):
        return self._configuration[config]

    def DELETE(self, route: str, handler: Handler, subdomain=DEFAULT):
        self.abettor(METHOD_DELETE, route, handler, subdomain)

    def GET(self, route: str, handler: Handler, subdomain=DEFAULT):
        self.abettor(METHOD_GET, route, handler, subdomain)

    def HEAD(self, route: str, handler: Handler, subdomain=DEFAULT):
        self.abettor(METHOD_HEAD, route, handler, subdomain)

    def HTTP(self, route: str, handler: Handler, subdomain=DEFAULT):
        for method in [CONNECT, DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT, TRACE]:
            self.abettor(method, route, handler, subdomain)

    def OPTIONS(self, route: str, handler: Handler, subdomain=DEFAULT):
        self.abettor(METHOD_OPTIONS, route, handler, subdomain)

    def PATCH(self, route: str, handler: Handler, subdomain=DEFAULT, stream=False):
        self.abettor(METHOD_PATCH, route, handler, subdomain, stream=stream)

    def POST(self, route: str, handler: Handler, subdomain=DEFAULT, stream=False):
        self.abettor(METHOD_POST, route, handler, subdomain, stream=stream)

    def PUT(self, route: str, handler: Handler, subdomain=DEFAULT, stream=False):
        self.abettor(METHOD_PUT, route, handler, subdomain, stream=stream)

    def TRACE(self, route: str, handler: Handler, subdomain=DEFAULT):
        self.abettor(METHOD_TRACE, route, handler, subdomain)

    def ON(self, *args):
        return self.ONCE(*args)

    def ONCE(self, *args):
        arguments = len(args)
        error_message = 'ONCE requires a callable argument as default'
        help_message = 'If 2 arguments provided: first: str = `startup` or `shutdown` AND second: Callable'
        try: assert arguments <= 2
        except: raise TypeError('ONCE function received more than 2 arguments')

        def closure(func):
            @wraps(func)
            async def hidden(r):
                if iscoroutinefunction(func): return await func(self)
                else: return func(self)
            return hidden

        if arguments == 1:
            first = args[0]
            try: assert isinstance(first, Callable)
            except AssertionError: raise TypeError(error_message)
            self.initializers.append(closure(first))
        else:
            first, second = args

            try: assert first.lower() in [STARTUP, SHUTDOWN]
            except (AssertionError, TypeError, AttributeError): raise ValueError(help_message)

            try:
                if isinstance(second, str): second = _string_to_function_handler(second)
                assert isinstance(second, Callable)
            except (ValueError, AssertionError): raise TypeError(error_message)

            if first.lower() == STARTUP: self.initializers.append(closure(second))
            else: self.deinitializers.append(closure(second))

    def TEMPLATES(self, folder: str, escape=None, asynchronous=True, relative_to=None, prefix=None):
        # TODO: add warning if root folder slash is used
        if relative_to: relative_file_path_folder = path.realpath(path.dirname(relative_to))
        else: relative_file_path_folder = getcwd()

        file_system_loader = FileSystemLoader(path.join(relative_file_path_folder, folder))
        files_to_escape = escape or ['htm', 'html']

        if prefix:
            new_loader = PrefixLoader({prefix: file_system_loader})
        else:
            new_loader = file_system_loader

        # Merge into existing environment if one exists
        if self._templater:
            current = self._templater.loader
            if isinstance(current, ChoiceLoader):
                current.loaders.append(new_loader)
            elif current:
                self._templater.loader = ChoiceLoader([current, new_loader])
            else:
                self._templater.loader = new_loader
        else:
            environment = Environment(loader=new_loader, autoescape=select_autoescape(files_to_escape))
            environment.is_async = asynchronous
            self._templater = environment

        self._loader = file_system_loader
        self._template_prefix = prefix

    def ASSETS(self, folder: str, route=None, subdomain=DEFAULT, relative_to=None):
        # TODO: add warning if root folder slash is used
        route = route or f'/{folder}/*'
        if relative_to: assets_folder_path = path.realpath(path.dirname(relative_to))
        else: assets_folder_path = path.realpath(getcwd())

        async def serve_assets(req: Request, res: Response, ctx: Context):
            static_asset = f"{req.params.get('*', '')}"
            location = path.join(assets_folder_path, f'{folder}')
            # `within` keeps the read inside the asset folder, so `..` segments and
            # symlinks leaving the tree resolve to a 404 rather than a file
            res.file(static_asset, within=location)
        self.GET(route, serve_assets, subdomain)

    def SOCKET(self, route: str, handler: Handler, subdomain=DEFAULT):
        self.WS(route, handler, subdomain)

    def WEBSOCKET(self, route: str, handler: Handler, subdomain=DEFAULT):
        self.WS(route, handler, subdomain)

    def WS(self, route: str, handler: Handler, subdomain=DEFAULT):
        self.abettor(METHOD_WEBSOCKET, route, handler, subdomain)

    def openapi(self):
        """Generate OpenAPI JSON specification"""
        paths = {}
        components = {"schemas": {}}
        
        def _register_schema(schema_cls, name=None):
            """Recursively register schemas and their definitions"""
            if not name:
                name = getattr(schema_cls, "__name__", "Model")
                
            # If already registered, return name
            if name in components["schemas"]:
                return name

            # Generate schema
            try:
                # Pytastic returns a JSON string, so we need to load it
                js_str = Pytastic().schema(schema_cls)
                js = loads(js_str)
            except Exception:
                # Fallback or error handling
                js = {"type": "object", "description": "Schema generation failed"}
            
            # Extract definitions if Pytastic eventually supports it or if we use a different mechanism
            # Currently Pytastic inlines definitions, so $defs might not be present or populated as msgspec does
            defs = js.pop("$defs", {})
            
            # If js is a reference to a local def, resolve it
            if "$ref" in js and js["$ref"].startswith("#/$defs/"):
                ref_name = js["$ref"].split("/")[-1]
                if ref_name in defs:
                    # The main schema IS this definition
                    js = defs.pop(ref_name)
            
            # Register remaining definitions
            for def_name, def_schema in defs.items():
                if def_name not in components["schemas"]:
                    components["schemas"][def_name] = def_schema
            
            # Register main schema
            components["schemas"][name] = js
            return name

        for (method, route, subdomain), meta in self.schema._schemas.items():
            documented, parameters = _openapi_path(route)
            path_item = paths.setdefault(documented, {})

            # 1. Determine Group (Tag)
            # Priority: Explicit 'group' > First meaningful URL segment > "Default"
            group = meta.get("group")
            if not group:
                # heuristic: /users/:id/orders -> users
                parts = [p for p in route.strip("/").split("/") if p and not p.startswith(":")]
                group = parts[0].capitalize() if parts else "Default"
            
            # Use provided summary or empty string
            summary = meta.get("summary") or ""
            op = {
                "tags": [group],
                "summary": summary,
                "description": meta.get("description") or "",
                "responses": {"200": {"description": "Successful Response"}}
            }
            if parameters: op["parameters"] = parameters

            expects = meta.get("expects")
            if expects:
                # Register schema and get name
                schema_name = _register_schema(expects)
                op["requestBody"] = {
                    "content": {
                        "application/json": {
                            "schema": {"$ref": f"#/components/schemas/{schema_name}"}
                        }
                    }
                }
            
            returns = meta.get("returns")
            if returns:
                schema_name = _register_schema(returns)
                op["responses"]["200"] = {
                    "description": "Successful Response",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": f"#/components/schemas/{schema_name}"}
                        }
                    }
                }
            
            path_item[method.lower()] = op
            
        return {
            "openapi": "3.1.0",
            "info": {
                "title": self._docs_config.get("title", "API Reference") if self._docs_config else "API Reference",
                "version": self._docs_config.get("version", "0.0.1") if self._docs_config else "0.0.1"
            },
            "paths": paths,
            "components": components
        }

    def DOCS(self, route: str, title="API Reference", version="0.0.1", subdomain=DEFAULT, favicon=None):
        self._docs_config = {"title": title, "version": version}

        async def openapi_handler(req, res, ctx):
            res.headers = "Content-Type", "application/json"
            res.body = dumps(self.openapi())

        json_path = f"{route.rstrip('/')}/openapi.json"
        self.GET(json_path, openapi_handler, subdomain=subdomain)

        favicon_tag = f'\n    <link rel="icon" href="{favicon}" />' if favicon else ""

        async def docs_handler(req, res, ctx):
            res.headers = "Content-Type", "text/html"
            res.body = f"""<!doctype html>
<html>
  <head>
    <title>{title}</title>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />{favicon_tag}
  </head>
  <body>
    <script id="api-reference" data-url="{json_path}"></script>
    <script src="https://cdn.jsdelivr.net/npm/@scalar/api-reference"></script>
  </body>
</html>"""
        self.GET(route, docs_handler, subdomain=subdomain)


class Application(Router):...
class App(Router):...
class Server(Router):...

