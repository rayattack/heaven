from collections import deque
from inspect import iscoroutinefunction

from uvicorn import run
from typing import Callable, Generic, TypeVar

from .constants import (
    CONNECT,
    DELETE,
    GET,
    HEAD,
    MESSAGE_NOT_FOUND,
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
    STATUS_NOT_FOUND,
    TRACE,
    URL_ERROR_MESSAGE
)

from .errors import AbortException, UrlError
from .request import HttpRequest
from .response import ResponseWriter
from .context import Context


methods = ['get', 'post', 'put', 'delete', 'connect', 'head', 'options', 'patch']


Handler = Callable[[HttpRequest, ResponseWriter], object]


MARK_PRESENT = 'yes father... (RIP Rev. Angus Fraser...)'
SEPARATOR = INDEX = "/"


def isparamx(r: str):
    return (':', r[1:],) if r.startswith(':') else (r, None,)


def isvariable(r: str):
    newr = ':' if r.startswith(':') else r
    return newr, newr != r or r == '*'


class Route(object):
    def __init__(self, route: str, handler: Callable) -> None:
        self.parameterized = False
        self.route = route
        self.handler = handler
        self.children = {}

    def add(self, pathstring: deque, handler):
        # We can do this with confidence because we use cache to ensure url mask not used twice
        node = self
        while pathstring:
            route = pathstring.popleft()
            url, parameterized = isparamx(route)
            current_node = node.children.get(route)
            if not current_node:
                url, func = None, None
                current_node = Route(url, func)
                node.children[route] = current_node
            node = current_node
            node.parameterized = parameterized
        node.handler = handler

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
                    if(node.children.get('*')):
                        route_at_deviation = '/'.join([route, *routes])
                        deviation_point = node.children.get('*')
                    node = current_node
                    continue

                wildcard = node.children.get('*')
                if wildcard:
                    r.params = '*', '/'.join([route, *routes])
                    return wildcard.route, wildcard.handler

                if deviation_point:
                    r.params = '*', route_at_deviation
                    return deviation_point.route, deviation_point.handler

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
    
    def retrieve(self, match: str):
        pass


class Routes(object):
    def __init__(self):
        self.afters = {}
        self.befores = {}

        self.cache = {CONNECT: {}, DELETE: {}, GET: {}, HEAD: {}, OPTIONS: {}, PATCH: {}, POST: {}, PUT: {}, TRACE: {}}
        self.routes = {}

    def add(self, method: str, route: str, handler: Callable):
        # ensure the method and route combo has not been already registered
        assert self.cache.get(method, {}).get(route) is None
        self.cache[method][route] = MARK_PRESENT

        # here we check and set the root to be a route node i.e. / with no handler
        # if necessary so we can traverse freely
        route_node: Route = self.routes.get(method)
        if not route_node:
            route_node = Route(None, None)
            self.routes[method] = route_node

        if route == SEPARATOR:
            route_node.route = route
            route_node.handler = handler
            return

        # Otherwise strip and split the routes into stops or stoppable stumps i.e. /customers /:id /orders
        routes = route.strip(SEPARATOR).split(SEPARATOR)

        # get the length of the routes so we can use for validation checks in a loop later
        stop_at = len(routes) - 1

        for index, routerling in enumerate(routes):
            routerling, parameterized = isparamx(routerling)
            new_route_node = route_node.children.get(routerling)
            if not new_route_node:
                new_route_node = Route(None, None)
                route_node.children[routerling] = new_route_node
            
            route_node = new_route_node
            route_node.parameterized = parameterized

            if index == stop_at:
                assert route_node.handler is None, f'Handler already registered for route: ${routerling}'
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

    async def handle(self, scope, receive, send):
        """
        Traverse internal route tree and use appropriate method
        """
        body = await receive()

        r = HttpRequest(scope, body, receive)
        w = ResponseWriter(scope)
        c = Context()

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
        if route == SEPARATOR:
            matched = route_node.route # same as = SEPARATOR
            handler = route_node.handler
        else:
            routes = route.strip(SEPARATOR).split('/')
            matched, handler = route_node.match(deque(routes), r)

        if not matched:
            return w

        # call all pre handle request hooks but first reset response_writer from not found to found
        w.status = 200; w.body = b''
        try:
            await self.xhooks(self.befores, matched, r, w, c)

            # call request handler
            if w._abort: raise AbortException
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

    async def xhooks(self, hookstore, matched, r: HttpRequest, w: ResponseWriter, c: Context):
        # traverse the before tree - changed to tree to match routes tree
        # for every * add it to list of hooks to call
        # if match also add functions there to list of hooks to call
        hooks = set(hookstore.get(matched, []))
        parts = matched.strip(SEPARATOR).split(SEPARATOR)
        for position, part in enumerate(parts):
            joinedparts = "/".join(parts[:position])
            _ = '' if position == 0 else SEPARATOR
            hooks.update(hookstore.get(f'/{joinedparts}{_}*', []))
        for hook in hooks:
            if w._abort: raise AbortException
            hook(r, w, c)


class Router(object):
    def __init__(self) -> None:
        self.rtx = Routes()
    
    async def __call__(self, scope, receive, send):
        response = await self.rtx.handle(scope, receive, send)
        await send({
            'type': 'http.response.start',
            'headers': response.headers,
            'status': response.status
        })
        await send({
            'type': 'http.response.body',
            'body': response.body
        }) 

    def abettor(self, method: str, route: str, handler: Handler):
        if not route.startswith('/'): raise UrlError
        self.rtx.add(method, route, handler)

    def AFTER(self, route: str, handler: Callable):
        if not route.startswith('/'): raise UrlError(URL_ERROR_MESSAGE)
        self.rtx.after = route, handler

    def BEFORE(self, route: str, handler: Callable):
        if not route.startswith('/'): raise UrlError(URL_ERROR_MESSAGE)
        self.rtx.before = route, handler

    def CONNECT(self, route: str, handler: Callable[[HttpRequest, ResponseWriter], object]):
        self.abettor(METHOD_CONNECT, route, handler)

    def DELETE(self, route: str, handler: Callable):
        self.abettor(METHOD_DELETE, route, handler)
    
    def GET(self, route: str, handler: Callable):
        self.abettor(METHOD_GET, route, handler)
    
    def HTTP(self, route: str, handler: Callable):
        for method in [CONNECT, DELETE, GET, OPTIONS, PATCH, POST, PUT, TRACE]:
            self.abettor(method, route, handler)
    
    def OPTIONS(self, route: str, handler: Callable):
        self.abettor(METHOD_OPTIONS, route, handler)
    
    def PATCH(self, route: str, handler: Callable):
        self.abettor(METHOD_PATCH, route, handler)
    
    def POST(self, route: str, handler: Callable):
        self.abettor(METHOD_POST, route, handler)
    
    def PUT(self, route: str, handler: Callable):
        self.abettor(METHOD_PUT, route, handler)
    
    def TRACE(self, route: str, handler: Callable):
        self.abettor(METHOD_TRACE, route, handler)

    def listen(self, host='localhost', port='8701', debug=False):
        # implement development server? uvicorn already present as dependency so not in python library
        pass
