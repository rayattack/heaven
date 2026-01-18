from asyncio import gather, get_running_loop, sleep as asleep
from collections import deque
from functools import wraps
from http import HTTPStatus
from importlib import import_module
from inspect import iscoroutinefunction
from os import path, getcwd
from typing import Any, Callable, Tuple, Union

import json
import mimetypes
import msgspec
from aiofiles import open as async_open_file
from jinja2 import Environment, FileSystemLoader, select_autoescape
from uvicorn import run

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
from .utils import preprocessor
from .request import Request
from .response import Response
from .context import Context, Look
from .errors import AbortException, SubdomainError, UrlDuplicateError, UrlError

methods = ['get', 'post', 'put', 'delete', 'connect', 'head', 'options', 'patch']

Handler = Union[Callable[[Request, Response, Context], object], str]

SEPARATOR = INDEX = "/"


def _closure_mounted_application(handler: Handler, mounted: 'Router'):
    async def delegate(req: Request, res: Response, ctx: Context):
        req.mounted = mounted
        res._mounted_from_application = mounted
        if iscoroutinefunction(handler): await handler(req, res, ctx)
        else: handler(req, res, ctx)
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


def _string_to_function_handler(handler: str):
    if type(handler) is str and '.' in handler:
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
        value = self._value
        param = self._potentials.get(parameter_address)

        stats = param.split(':')
        if len(stats) == 2: key, kind = stats
        else: key, kind = param, ''
        cast = {'int': int, 'str': str}.get(kind.lower())

        # no need for if use None to cast fails and cast only exists deliberately
        try: value = cast(value)
        except: pass
        return key, value



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

        # grand father deviation point in case we are dealing from the start with a catch all route
        deviation_point: Route = node.children.get('*')

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


        # time to process what parameters we saw
        for parameter in parameters:
            r.params = parameter.resolve(node.route)
        # default node.route is None and handler as well
        # so this returns None if no route encountered or what was encountered in while block above
        r.qh = node.queryhint
        return node.route, node.handler

    def not_found(self, r: Request, w: Response, c: Context):
        w.status = 404
        w.body = b'Not found'


class Routes(object):
    def __init__(self):
        self.afters = {}
        self.befores = {}

        self.cache = {CONNECT: {}, DELETE: {}, GET: {}, HEAD: {}, OPTIONS: {}, PATCH: {}, POST: {}, PUT: {}, TRACE: {}, SOCKET: {}}
        self.routes = {}

    def add(self, method: str, route: str, handler: Callable, router: 'Router'):
        """
        method: one of POST, GET, OPTIONS... etc - i.e. the HTTP method
        route: the route url/endpoint
        handler: function corresponding to the signature of a heaven handler
        """
        queryhint = ''
        if len(route.split('?')) > 1:
            route, queryhint = route.split('?', 1)

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
            new_route_node = route_node.children.get(label)
            if not new_route_node:
                new_route_node = Route(None, None, router)
                route_node.children[label] = new_route_node

            route_node = new_route_node
            if remainder: route_node.parameterized[route] = remainder

            if index == stop_at:
                assert route_node.handler is None, f'Handler already registered for route: ${_heaven}'
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

    def get_handler(self, routes):
        for route in routes:...
        return None, None

    async def handle(self, scope, receive, send, metadata=None, application=None):
        """
        Traverse internal route tree and use appropriate method
        """
        method = scope.get('method')
        if scope['type'] == 'websocket': method = SOCKET

        body = b''
        if scope['type'] == 'http':
            more = True
            while more:
                msg = await receive()
                body += msg.get('body', b'')
                more = msg.get('more_body', False)

        r = Request(scope, body, receive, metadata, application)
        c = Context(application)
        w = Response(context=c, app=application, request=r)

        matched = None
        handler = None

        # if the cache has nothing under its GET, POST etc it means nothing's been registered and we can leave early
        roots = self.cache.get(method, {})
        if not roots: return w

        # if no route node then no methods have been registered
        route_node = self.routes.get(method)
        matched_node = route_node
        if not route_node: return w

        route = scope.get('path')
        if route == SEPARATOR: #pragma: nocover
            matched = route_node.route # same as = SEPARATOR
            handler = route_node.handler
        else:
            routes = route.strip(SEPARATOR).split('/')
            matched, handler = route_node.match(deque(routes), r)

        if not matched: return w

        r._application = route_node.heaven_instance
        r._route = matched

        # call all pre handle request hooks but first reset response_writer from not found to found
        w.status = 200; w.body = b''
        try:
            await self.xhooks(self.befores, matched, r, w, c)

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
                    msg = await receive()
                    return msg.get('text') or msg.get('bytes')

                if iscoroutinefunction(handler): await handler(sender, receiver, r, c)
                else: handler(sender, receiver, r, c)
            else:
                if iscoroutinefunction(handler): await handler(r, w, c)
                else: handler(r, w, c)

            # call all post handle request hooks
            await self.xhooks(self.afters, matched, r, w, c)
        except AbortException:
            return w

        # too many hooks is not good for the pan ;-)
        # i.e. hook lookup is constant but running many hooks will
        # increase the time it takes before the response is released to the network
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

    async def xhooks(self, hookstore, matched, r: Request, w: Response, c: Context):
        hooks = set(hookstore.get(matched, []))
        """Here we are getting any and or all hooks that match the url verbatim as provided
        i.e. /url/:id or /url/:id/nested
        """

        parts = matched.strip(SEPARATOR).split(SEPARATOR)
        for position, part in enumerate(parts):
            joinedparts = "/".join(parts[:position])
            _ = '' if position == 0 else SEPARATOR
            hooks.update(hookstore.get(f'/{joinedparts}{_}*', []))
        """Next we clean the matched url of any '/' surpluses before splitting it into a list
        for enumeration.
        Enumeration helps us gradually use the current enumeration position/offset/index to
        gradually append '*' until we get a match.
        """

        for hook in hooks:
            if w._abort: raise AbortException
            
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

    def add(self, method: str, route: str, expects=None, returns=None, summary=None, description=None, protect=None, partial=None, strict=None, group=None, subdomain=DEFAULT):
        self._schemas[(method.upper(), route, subdomain)] = {
            'expects': _string_to_function_handler(expects),
            'returns': _string_to_function_handler(returns),
            'summary': summary,
            'description': description,
            'protect': protect,
            'partial': partial,
            'strict': strict,
            'group': group
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
    def HTTP(self, route: str, handler: Handler): self.app.HTTP(route, handler, subdomain=self.name)
    def OPTIONS(self, route: str, handler: Handler): self.app.OPTIONS(route, handler, subdomain=self.name)
    def PATCH(self, route: str, handler: Handler): self.app.PATCH(route, handler, subdomain=self.name)
    def POST(self, route: str, handler: Handler): self.app.POST(route, handler, subdomain=self.name)
    def PUT(self, route: str, handler: Handler): self.app.PUT(route, handler, subdomain=self.name)
    def TRACE(self, route: str, handler: Handler): self.app.TRACE(route, handler, subdomain=self.name)
    def SOCKET(self, route: str, handler: Handler): self.app.SOCKET(route, handler, subdomain=self.name)
    def WEBSOCKET(self, route: str, handler: Handler): self.app.WEBSOCKET(route, handler, subdomain=self.name)
    def WS(self, route: str, handler: Handler): self.app.WS(route, handler, subdomain=self.name)
    def assets(self, folder: str, route=None, relative_to=None): self.app.ASSETS(folder, route, subdomain=self.name, relative_to=relative_to)
    def abettor(self, method: str, route: str, handler: Handler): self.app.abettor(method, route, handler, subdomain=self.name)
    def doc(self, route: str, title="API Reference", version="0.0.1"): self.app.DOCS(route, title, version, subdomain=self.name)


class Router(object):
    def __init__(self, configurator=None, protect_output=True, allow_partials=False, fail_on_output=True, debug=True):
        self._debug = debug
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
        self.__daemons = []
        self.schema = SchemaRegistry(self)
        self._docs_config = None
        self._baked = False
        self._protect_output = protect_output
        self._allow_partials = allow_partials
        self._fail_on_output = fail_on_output

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
            if expects and hasattr(expects, '__struct_fields__'):
                decoder = msgspec.json.Decoder(expects)
                async def validate_hook(req, res, ctx, dec=decoder):
                    try:
                        req._data = dec.decode(req.body)
                    except msgspec.ValidationError as e:
                        res.status = 422
                        res.body = str(e).encode()
                        res.abort(res.body)
                self.BEFORE(route, validate_hook, subdomain=subdomain)
            
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
                    # Skip if body is already bytes/generator (user manually handled it)
                    if isinstance(res.body, (bytes, str)) or hasattr(res.body, '__aiter__'):
                        return

                    try:
                        # 1. Clean if enabled - msgspec.convert drops extra fields by default
                        if protect:
                            res.body = msgspec.convert(res.body, type=schema)
                        
                        # 2. Encode to JSON
                        res.headers = "Content-Type", "application/json"
                        res.body = msgspec.json.encode(res.body)
                    except Exception as e:
                        # If partial matching is enabled, we might want to try encoding without conversion if conversion failed
                        if partial and protect:
                            try:
                                res.headers = "Content-Type", "application/json"
                                res.body = msgspec.json.encode(res.body)
                                return # Success with partial (original data)
                            except: pass

                        if strict:
                            res.status = 500
                            res.body = f"Output Validation Error: {str(e)}".encode()
                        else:
                            print(f"Heaven Output Warning [{req.route}]: {str(e)}")
                            # Fallback to normal encoding
                            res.headers = "Content-Type", "application/json"
                            res.body = msgspec.json.encode(res.body)
                
                self.AFTER(route, output_hook, subdomain=subdomain)
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
        engine = self.subdomains.get(subdomain)
        if not engine:
            engine = wildcard_engine if wildcard_engine else self.subdomains.get(DEFAULT)

        if not self._baked: self._bake_schemas()

        try:
            response = await engine.handle(scope, receive, send, metadata, self)

            # Auto-serialize dict/list bodies to JSON if not already handled
            if isinstance(response.body, (dict, list)):
                try:
                    response.body = msgspec.json.encode(response.body)
                    # Ensure Content-Type is set to application/json if missing
                    if not any(h[0].lower() == b'content-type' for h in response.headers):
                        response.header('Content-Type', 'application/json')
                except Exception as e:
                    print(f"JSON Serialization Error: {e}")
                    response.status = 500
                    response.body = b"Internal Server Error: JSON Serialization Failed"
                    # Clear headers and set content-type plain
                    response._headers = []
                    response.header('Content-Type', 'text/plain')
        except Exception as e:
            if not self._debug: raise e
            # Guardian Angel
            from .response import _get_guardian_angel
            # Create a dummy response/request context for the angel if needed
            # But we need a valid request object for the template
            # If handle failed, 'r' might not be available here, but we can reconstruct a basic one or use a dummy
            # Actually, engine.handle creates the request. If it fails *inside* handle, we don't have reference to 'r' here
            # unless we move the try/catch inside engine.handle or reconstruct.
            # Best approach: catch inside engine.handle? No, that returns a response.
            # Quickest valid object:
            r = Request(scope, b'', receive, metadata, self)
            c = Context(self)
            response = Response(self, c, r)
            _get_guardian_angel(response, e)
        
        if scope['type'] == 'http':
            await send({'type': 'http.response.start', 'headers': response.headers, 'status': response.status})
            if hasattr(response.body, '__aiter__'):
                async for chunk in response.body:
                    await send({'type': 'http.response.body', 'body': chunk, 'more_body': True})
                await send({'type': 'http.response.body', 'body': b'', 'more_body': False})
            else:
                await send({'type': 'http.response.body', 'body': response.body, **response.metadata})
        else:
            await send({'type': 'websocket.http.response.start', 'headers': response.headers, 'status': response.status})

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

    def abettor(self, method: str, route: str, handler: Handler, subdomain=DEFAULT, router = None):
        if not route.startswith('/'): raise UrlError(f'{route} is not a valid route - must start with /')
        handler = _string_to_function_handler(handler)
        engine = self.subdomains.get(subdomain)
        if not isinstance(engine, Routes):
            raise SubdomainError
        engine.add(method, route, handler, router or self)

    def call(self, handler: str, *args, **kwargs):
        if isinstance(handler, str): handler = _string_to_function_handler(handler)
        handler(self, *args, **kwargs)
        return self

    @property
    def daemons(self):
        return self.__daemons

    @daemons.setter
    def daemons(self, afunction):
        @wraps(afunction)
        async def _daemon(app):
            loop = get_running_loop()
            if (iscoroutinefunction(afunction)): 
                sleeps = await afunction(app)
            else: 
                # Run sync functions in a thread pool to avoid blocking the event loop
                sleeps = await loop.run_in_executor(None, afunction, app)
            
            if sleeps is None or sleeps == False: return
            await asleep(sleeps)
            loop.create_task(_daemon(app))
        self.__daemons.append(_daemon)

    def keep(self, key, value):
        self._buckets[key] = value

    def unkeep(self, key):
        value = self._buckets[key]
        del self._buckets[key]
        return value

    def peek(self, key):
        try: value = self._buckets[key]
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

    def cors(self, handler=None, **kwargs):
        """
        Enables Cross-Origin Resource Sharing (CORS) for the application.
        Accepts a handler function or configuration via kwargs.
        """
        if handler and callable(handler):
            self.BEFORE("/*", handler)
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

        self.BEFORE("/*", handle_cors)
        return self

    def sessions(self, secret_key, cookie_name="session", max_age=3600):
        """
        Enables secure, signed cookie-based sessions.
        """
        from .security import SecureSerializer
        serializer = SecureSerializer(secret_key)

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
            ctx._initial_session = msgspec.json.encode(data)

        async def save_session(req, res, ctx):
            if not hasattr(ctx, 'session'): return
            
            # Check if session was modified
            # We access _data directly because ctx.session is a Look wrapper around the dict
            current_data = ctx.session._data if hasattr(ctx.session, '_data') else ctx.session
            try:
                current = msgspec.json.encode(current_data)
            except: return

            if current == getattr(ctx, '_initial_session', b''):
                return

            # Sign and Serialize
            token = serializer.dumps(current_data)
            
            # Set cookie header
            cookie_val = f"{cookie_name}={token}; Path=/; HttpOnly; SameSite=Lax; Max-Age={max_age}"
            res.headers = "Set-Cookie", cookie_val

        self.BEFORE("/*", load_session)
        self.AFTER("/*", save_session)
        return self

    def listen(self, host='localhost', port='8701', debug=True, **kwargs): #pragma: nocover
        run(self, host=host, port=port, debug=debug, **kwargs)

    def subdomain(self, subdomain: str):
        if not self.subdomains.get(subdomain):
            self.subdomains[subdomain] = Routes()
        return SubdomainContext(self, subdomain)

    def mount(self, router: 'Router', isolated = True):
        if not isolated:
            self._buckets = {**router._buckets, **self._buckets}
            self._configuration = {**router._configuration, **self._configuration}
            if self._loader and router._loader:
                self._loader.searchpath = [*router._loader.searchpath, *self._loader.searchpath]

        self.deinitializers.extend(router.deinitializers)
        self.initializers.extend(router.initializers)

        for subdomain in router.subdomains:
            engine: Routes = router.subdomains[subdomain]
            for method in engine.cache:
                cache = engine.cache[method]
                for route in cache:
                    handler = cache[route]
                    self.subdomain(subdomain)
                    closured_handler = _closure_mounted_application(handler, router)
                    self.abettor(method, route, closured_handler, subdomain=subdomain, router=router if isolated else self)
            for after in engine.afters:
                self.subdomains[subdomain].afters[after] = [*engine.afters[after], *self.subdomains[subdomain].afters.get(after, [])]
            for before in engine.befores:
                self.subdomains[subdomain].befores[before] = [*engine.befores[before], *self.subdomains[subdomain].befores.get(before, [])]

    def websocket(self):
        # only if app is already running
        if(self.__ws): return
        self.__ws = True

    @property
    def ws(self):
        return self.__ws

    def AFTER(self, route: str, handler: Handler, subdomain=DEFAULT):
        if not route.startswith('/'): raise UrlError(URL_ERROR_MESSAGE)
        engine = self.subdomains.get(subdomain)
        if not isinstance(engine, Routes): #pragma: nocover
            raise NameError('Subdomain does not exist - register subdomain on router first')
        handler = _string_to_function_handler(handler)
        engine.after = route, handler

    def BEFORE(self, route: str, handler: Handler, subdomain=DEFAULT):
        if not route.startswith('/'): raise UrlError(URL_ERROR_MESSAGE)
        engine = self.subdomains.get(subdomain)
        if not isinstance(engine, Routes): #pragma: nocover
            raise NameError('Subdomain does not exist - register subdomain on router first')
        handler = _string_to_function_handler(handler)
        engine.before = route, handler

    def CONNECT(self, route: str, handler: Handler, subdomain=DEFAULT):
        self.abettor(METHOD_CONNECT, route, handler, subdomain)

    def CONFIG(self, config):
        return self._configuration[config]

    def DELETE(self, route: str, handler: Handler, subdomain=DEFAULT):
        self.abettor(METHOD_DELETE, route, handler, subdomain)

    def GET(self, route: str, handler: Handler, subdomain=DEFAULT):
        self.abettor(METHOD_GET, route, handler, subdomain)

    def HTTP(self, route: str, handler: Handler, subdomain=DEFAULT):
        for method in [CONNECT, DELETE, GET, OPTIONS, PATCH, POST, PUT, TRACE]:
            self.abettor(method, route, handler, subdomain)

    def OPTIONS(self, route: str, handler: Handler, subdomain=DEFAULT):
        self.abettor(METHOD_OPTIONS, route, handler, subdomain)

    def PATCH(self, route: str, handler: Handler, subdomain=DEFAULT):
        self.abettor(METHOD_PATCH, route, handler, subdomain)

    def POST(self, route: str, handler: Handler, subdomain=DEFAULT):
        self.abettor(METHOD_POST, route, handler, subdomain)

    def PUT(self, route: str, handler: Handler, subdomain=DEFAULT):
        self.abettor(METHOD_PUT, route, handler, subdomain)

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

    def TEMPLATES(self, folder: str, escape=None, asynchronous=True, relative_to=None):
        # TODO: add warning if root folder slash is used
        if relative_to: relative_file_path_folder = path.realpath(path.dirname(relative_to))
        else: relative_file_path_folder = getcwd()

        file_system_loader = FileSystemLoader(path.join(relative_file_path_folder, folder))
        files_to_escape = escape or ['htm', 'html']
        environment = Environment(loader=file_system_loader, autoescape=select_autoescape(files_to_escape))
        environment.is_async = asynchronous
        self._templater = environment
        self._loader = file_system_loader

    def ASSETS(self, folder: str, route=None, subdomain=DEFAULT, relative_to=None):
        # TODO: add warning if root folder slash is used
        route = route or f'/{folder}/*'
        if relative_to: assets_folder_path = path.realpath(path.dirname(relative_to))
        else: assets_folder_path = path.realpath(getcwd())

        async def serve_assets(req: Request, res: Response, ctx: Context):
            static_asset = f"{req.params.get('*', '')}"
            location = path.join(assets_folder_path, f'{folder}')
            target_resource_path = path.join(location, static_asset)
            res.file(target_resource_path)
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
            js = msgspec.json.schema(schema_cls)
            
            # Extract definitions
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
            path_item = paths.setdefault(route, {})
            
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

    def DOCS(self, route: str, title="API Reference", version="0.0.1", subdomain=DEFAULT):
        self._docs_config = {"title": title, "version": version}
        
        async def openapi_handler(req, res, ctx):
            res.headers = "Content-Type", "application/json"
            res.body = json.dumps(self.openapi())

        json_path = f"{route.rstrip('/')}/openapi.json"
        self.GET(json_path, openapi_handler, subdomain=subdomain)

        async def docs_handler(req, res, ctx):
            res.headers = "Content-Type", "text/html"
            res.body = f"""<!doctype html>
<html>
  <head>
    <title>{title}</title>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
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

