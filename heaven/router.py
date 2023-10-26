from asyncio import gather
from collections import deque
from functools import wraps
from http import HTTPStatus
from importlib import import_module
from inspect import iscoroutinefunction
from os import path, getcwd

from aiofiles import open as async_open_file
from jinja2 import Environment, FileSystemLoader, select_autoescape

from typing import Callable, Union

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
    OPTIONS,
    PATCH,
    POST,
    PUT,
    SHUTDOWN,
    STARTUP,
    TRACE,
    URL_ERROR_MESSAGE,
    WILDCARD
)

from .errors import AbortException, SubdomainError, UrlDuplicateError, UrlError
from .utils import preprocessor
from .request import Request
from .response import Response
from .context import Context


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
    ct = 'Content-Type'
    if(req.url.endswith('.css')): res.headers = ct, 'text/css'
    elif(req.url.endswith('.svg')): res.headers = ct, 'image/svg+xml'
    elif(req.url.endswith('.js')): res.headers = ct, 'text/javascript'


def _string_to_function_handler(handler: str):
    if isinstance(handler, str):
        module_name, function_name = handler.rsplit('.', 1)
        module = import_module(module_name)
        handler = getattr(module, function_name)
    return handler


class Route(object):
    def __init__(self, route: str, handler: Callable, router: 'Router') -> None:
        self.heaven_instance = router
        self.parameterized = False
        self.route = route
        self.handler = handler
        self.children = {}

    def match(self, routes: deque, r: Request):
        matched: str = None
        node: Route = self
        route_at_deviation = '/'.join(routes)
        deviation_point: Route = node.children.get('*')
        while routes:
            route = routes.popleft()
            current_node = node.children.get(route)
            if not current_node:
                # is there a parameterized child?
                current_node = node.children.get(':')
                if current_node:
                    """Store the label that immediately follows the ':' represented by paremeterized
                    and its value represented as route into request.params"""
                    r.params = current_node.parameterized, route

                    if(node.children.get('*')):
                        """If there was also a wildcard seeing as placeholder ':' takes precedence, then
                        mark the point it deviated so it is possible to backtrack and use that point for
                        matching if this path fumbles later"""
                        route_at_deviation = '/'.join([route, *routes])
                        deviation_point = node.children.get('*')

                    node = current_node
                    continue

                wildcard = node.children.get('*')
                if wildcard:  #pragma: nocover
                    r.params = '*', '/'.join([route, *routes])
                    return wildcard.route, wildcard.handler

                if deviation_point:
                    r.params = '*', route_at_deviation
                    return deviation_point.route, deviation_point.handler
                """This is one place where the deviation point is used - the remainder of the url supplied is
                passed into request.params as the value for '*' for optional lookup purposes"""

                return matched, self.not_found
            node = current_node
                
        # was there a wildcard encountered along the way
        if deviation_point and not node.route:
            r.params = '*', route_at_deviation
            return deviation_point.route, deviation_point.handler
        return node.route, node.handler
    
    def not_found(self, r: Request, w: Response, c: Context):
        w.status = 404
        w.body = b'Not found'


class Routes(object):
    def __init__(self):
        self.afters = {}
        self.befores = {}

        self.cache = {CONNECT: {}, DELETE: {}, GET: {}, HEAD: {}, OPTIONS: {}, PATCH: {}, POST: {}, PUT: {}, TRACE: {}}
        self.routes = {}

    def add(self, method: str, route: str, handler: Callable, router: 'Router'):
        """
        method: one of POST, GET, OPTIONS... etc - i.e. the HTTP method
        route: the route url/endpoint
        handler: function corresponding to the signature of a heaven handler
        """
        # ensure the method and route combo has not been already registered
        try: assert self.cache.get(method, {}).get(route) is None
        except AssertionError: raise UrlDuplicateError

        self.cache[method][route] = handler

        # here we check and set the root to be a route node i.e. / with no handler
        # if necessary so we can traverse freely
        route_node: Route = self.routes.get(method)
        if not route_node:
            route_node = Route(None, None, router)
            self.routes[method] = route_node

        if route == SEPARATOR:
            route_node.route = route
            route_node.handler = handler
            return

        # Otherwise strip and split the routes into stops or stoppable
        # stumps i.e. /customers/:id/orders -> [customers, :id, orders]
        routes = route.strip(SEPARATOR).split(SEPARATOR)

        # get the length of the routes so we can use for validation checks in a loop later
        stop_at = len(routes) - 1

        for index, heaven in enumerate(routes):
            _heaven, _parameterized = _isparamx(heaven)
            new_route_node = route_node.children.get(_heaven)
            if not new_route_node:
                new_route_node = Route(None, None, router)
                route_node.children[_heaven] = new_route_node
            
            route_node = new_route_node
            route_node.parameterized = _parameterized

            if index == stop_at:
                assert route_node.handler is None, f'Handler already registered for route: ${_heaven}'
                route_node.route = route
                route_node.handler = handler
    
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
        body = b''
        more = True
        while more:
            msg = await receive()
            body += msg.get('body', b'')
            more = msg.get('more_body', False)

        r = Request(scope, body, receive, metadata, application)
        c = Context(application)
        w = Response(context=c, app=application)

        method = scope.get('method')
        matched = None
        handler = None

        # if the cache has nothing under its GET, POST etc it means nothing's been registered and we can leave early
        roots = self.cache.get(method, {})
        if not roots:
            return w

        # if no route node then no methods have been registered
        route_node = self.routes.get(method)
        if not route_node:
            return w

        route = scope.get('path')
        if route == SEPARATOR: #pragma: nocover
            matched = route_node.route # same as = SEPARATOR
            handler = route_node.handler
        else:
            routes = route.strip(SEPARATOR).split('/')
            matched, handler = route_node.match(deque(routes), r)

        if not matched:
            return w

        r._application = route_node.heaven_instance

        # call all pre handle request hooks but first reset response_writer from not found to found
        w.status = 200; w.body = b''
        try:
            await self.xhooks(self.befores, matched, r, w, c)

            # call request handler
            if w._abort: raise AbortException
            try: handler.__requesthandler__
            except: pass
            else: handler = handler.__call__
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
        We stop at a level before matched/masked url as we already searched for verbatim match
        hence no index + 1 used
        """

        for hook in hooks:
            if w._abort: raise AbortException
            if iscoroutinefunction(hook): await hook(r, w, c)
            else: hook(r, w, c)


class Router(object):
    def __init__(self, configurator=None):
        self.finalized = False
        self.initializers = deque()
        self.deinitializers = deque()
        self.subdomains = {}
        self.subdomains[DEFAULT] = Routes()
        self._buckets = {}
        self._configuration = _get_configuration(configurator)
        self._templater = None
        self._loader = None

    async def __call__(self, scope, receive, send):
        if scope['type'] == 'lifespan':
            while True:
                message = await receive()
                if message['type'] == 'lifespan.startup':
                    try: await self._register()
                    except: _notify()
                    await send({'type': 'lifespan.startup.complete'})
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

        response = await engine.handle(scope, receive, send, metadata, self)
        await send({'type': 'http.response.start', 'headers': response.headers, 'status': response.status})
        await send({'type': 'http.response.body', 'body': response.body, **response.metadata})

        # add background tasks
        if response.deferred:
            await gather(*[func(self) for func in response._deferred])

    def abettor(self, method: str, route: str, handler: Handler, subdomain=DEFAULT, router = None):
        if not route.startswith('/'): raise UrlError
        handler = _string_to_function_handler(handler)
        engine = self.subdomains.get(subdomain)
        if not isinstance(engine, Routes):
            raise SubdomainError
        engine.add(method, route, handler, router or self)

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

            try: assert isinstance(second, Callable)
            except AssertionError: raise TypeError(error_message)

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

    def ASSETS(self, folder: str, route='/public/*', subdomain=DEFAULT, relative_to=None):
        # TODO: add warning if root folder slash is used
        if relative_to: assets_folder_path = path.realpath(path.dirname(relative_to))
        else: assets_folder_path = path.realpath(getcwd())

        async def serve_assets(req: Request, res: Response, ctx: Context):
            static_asset = f"{req.params.get('*', '')}"
            location = path.join(assets_folder_path, f'{folder}')
            target_resource_path = path.join(location, static_asset)
            try:
                async with async_open_file(target_resource_path, 'rb') as opened_asset_file:
                    _set_content_type(req, res)
                    res.body = b''.join(await opened_asset_file.readlines())
            except Exception as exc:
                print(exc)
                res.status = HTTPStatus.NOT_FOUND
        self.GET(route, serve_assets, subdomain)

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

    def listen(self, host='localhost', port='8701', debug=DEFAULT): #pragma: nocover
        # repurpose this for websockets?
        pass

    def subdomain(self, subdomain: str):
        if self.subdomains.get(subdomain): return
        self.subdomains[subdomain] = Routes()

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


class Application(Router):...
class App(Router):...
class Server(Router):...
