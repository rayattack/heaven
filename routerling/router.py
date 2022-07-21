from collections import deque
from functools import wraps
from inspect import iscoroutinefunction

from typing import Callable

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
    TRACE,
    URL_ERROR_MESSAGE
)

from .errors import AbortException, SubdomainError, UrlDuplicateError, UrlError
from .utils import preprocessor
from .request import HttpRequest
from .response import ResponseWriter
from .context import Context


methods = ['get', 'post', 'put', 'delete', 'connect', 'head', 'options', 'patch']


Handler = Callable[[HttpRequest, ResponseWriter], object]

SEPARATOR = INDEX = "/"


def _get_configuration(configurator=None):
    if not configurator: return {}
    if isinstance(configurator, dict): return configurator
    return configurator()


def _isparamx(r: str):
    return (':', r[1:],) if r.startswith(':') else (r, None,)


def _notify(width=80, event='startup'): #pragma: nocover
    drawline = lambda: print('=' * width)
    drawline()
    print(f'NOTE: The `LAST` {event} func above failed and prevented others from running')
    drawline()


class Route(object):
    def __init__(self, route: str, handler: Callable, router: 'Router') -> None:
        self.routerling_instance = router
        self.parameterized = False
        self.route = route
        self.handler = handler
        self.children = {}

    def match(self, routes: deque, r: HttpRequest):
        matched: str = None
        route_at_deviation = None
        deviation_point: Route = None
        node: Route = self
        while routes:
            route = routes.popleft()
            current_node = node.children.get(route)
            if not current_node:
                # is there a parameterized child?
                current_node = node.children.get(':')
                if current_node:
                    r.params = current_node.parameterized, route
                    """Store the label that immediately follows the ':' represented by paremeterized
                    and its value represented as route into request.params"""

                    if(node.children.get('*')):
                        route_at_deviation = '/'.join([route, *routes])
                        deviation_point = node.children.get('*')
                    """If there was also a wildcard seeing as placeholder ':' takes precedence, then
                    mark the point it deviated so it is possible to backtrack and use that point for
                    matching if this path fumbles later"""

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
    
    def not_found(self, r: HttpRequest, w: ResponseWriter, c: Context):
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
        handler: function corresponding to the signature of a routerling handler
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

        for index, routerling in enumerate(routes):
            _routerling, _parameterized = _isparamx(routerling)
            new_route_node = route_node.children.get(_routerling)
            if not new_route_node:
                new_route_node = Route(None, None, router)
                route_node.children[_routerling] = new_route_node
            
            route_node = new_route_node
            route_node.parameterized = _parameterized

            if index == stop_at:
                assert route_node.handler is None, f'Handler already registered for route: ${_routerling}'
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

        r = HttpRequest(scope, body, receive, metadata, application)
        w = ResponseWriter()
        c = Context(application)

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

        r._application = route_node.routerling_instance

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
        for index, routerling in enumerate(routes):
            _routerling, _parameterized = _isparamx(routerling)
            route_node = route_node.children.get(_routerling)
            if not route_node:
                return
            if index == stop_at:
                route_node.route = None
                route_node.handler = None
                self.cache[method][route] = None

    async def xhooks(self, hookstore, matched, r: HttpRequest, w: ResponseWriter, c: Context):
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
                    except: _notify(event='shutdown')
                    await send({'type': 'lifespan.shutdown.complete'})

        metadata = preprocessor(scope)
        engine = self.subdomains.get(metadata[0]) or self.subdomains.get(DEFAULT)

        response = await engine.handle(scope, receive, send, metadata, self)
        await send({'type': 'http.response.start', 'headers': response.headers, 'status': response.status})
        await send({'type': 'http.response.body', 'body': response.body, **response.metadata})

    def abettor(self, method: str, route: str, handler: Handler, subdomain=DEFAULT, router = None):
        if not route.startswith('/'): raise UrlError
        engine = self.subdomains.get(subdomain)
        if not isinstance(engine, Routes):
            raise SubdomainError
        engine.add(method, route, handler, router or self)

    def AFTER(self, route: str, handler: Callable, subdomain=DEFAULT):
        if not route.startswith('/'): raise UrlError(URL_ERROR_MESSAGE)
        engine = self.subdomains.get(subdomain)
        if not isinstance(engine, Routes): #pragma: nocover
            raise NameError('Subdomain does not exist - register subdomain on router first')
        engine.after = route, handler

    def BEFORE(self, route: str, handler: Callable, subdomain=DEFAULT):
        if not route.startswith('/'): raise UrlError(URL_ERROR_MESSAGE)
        engine = self.subdomains.get(subdomain)
        if not isinstance(engine, Routes): #pragma: nocover
            raise NameError('Subdomain does not exist - register subdomain on router first')
        engine.before = route, handler

    def CONNECT(self, route: str, handler: Callable[[HttpRequest, ResponseWriter], object], subdomain=DEFAULT):
        self.abettor(METHOD_CONNECT, route, handler, subdomain)

    def CONFIG(self, config):
        return self._configuration[config]

    def DELETE(self, route: str, handler: Callable, subdomain=DEFAULT):
        self.abettor(METHOD_DELETE, route, handler, subdomain)
    
    def GET(self, route: str, handler: Callable, subdomain=DEFAULT):
        self.abettor(METHOD_GET, route, handler, subdomain)
    
    def HTTP(self, route: str, handler: Callable, subdomain=DEFAULT):
        for method in [CONNECT, DELETE, GET, OPTIONS, PATCH, POST, PUT, TRACE]:
            self.abettor(method, route, handler, subdomain)
    
    def OPTIONS(self, route: str, handler: Callable, subdomain=DEFAULT):
        self.abettor(METHOD_OPTIONS, route, handler, subdomain)
    
    def PATCH(self, route: str, handler: Callable, subdomain=DEFAULT):
        self.abettor(METHOD_PATCH, route, handler, subdomain)
    
    def POST(self, route: str, handler: Callable, subdomain=DEFAULT):
        self.abettor(METHOD_POST, route, handler, subdomain)
    
    def PUT(self, route: str, handler: Callable, subdomain=DEFAULT):
        self.abettor(METHOD_PUT, route, handler, subdomain)
    
    def TRACE(self, route: str, handler: Callable, subdomain=DEFAULT):
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

            try: assert first.lower() in ['startup', 'shutdown']
            except (AssertionError, TypeError, AttributeError): raise ValueError(help_message)

            try: assert isinstance(second, Callable)
            except AssertionError: raise TypeError(error_message)

            if first.lower() == 'startup': self.initializers.append(closure(second))
            else: self.deinitializers.append(closure(second))

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

        self.deinitializers.extend(router.deinitializers)
        self.initializers.extend(router.initializers)

        for subdomain in router.subdomains:
            engine: Routes = router.subdomains[subdomain]
            for method in engine.cache:
                cache = engine.cache[method]
                for route in cache:
                    handler = cache[route]
                    self.subdomain(subdomain)
                    self.abettor(method, route, handler, subdomain=subdomain, router=router if isolated else self)
            for after in engine.afters:
                self.subdomains[subdomain].afters[after] = [*engine.afters[after], *self.subdomains[subdomain].afters.get(after, [])]
            for before in engine.befores:
                self.subdomains[subdomain].befores[before] = [*engine.befores[before], *self.subdomains[subdomain].befores.get(before, [])]
