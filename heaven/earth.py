import json
from typing import Union, Any, Dict, Optional, Tuple
from .constants import DEFAULT, GET, POST, PUT, DELETE, PATCH
from .mocks import _listify_headers, MockRequest, MockResponse, MockContext
from .request import Request
from .response import Response
from .context import Context

class Earth:
    def __init__(self, app):
        self._app = app
        self._session_headers = {}
        self._session_cookies = {}
        self._track_session = False
        self._swaps = {}

    def swap(self, old_func, new_func):
        """Register a hook to be swapped during tests"""
        self._swaps[old_func] = new_func

    # Atomic factories
    def request(self, url: str, method: str = 'GET', body: Any = b'', headers: Dict = None, **kwargs) -> Request:
        h = {**self._session_headers, **(headers or {})}
        return MockRequest(url=url, method=method, body=body, headers=h, **kwargs)

    def response(self, req: Request = None) -> Response:
        ctx = Context(self._app)
        return Response(self._app, ctx, req or self.request('/'))

    def context(self) -> Context:
        return Context(self._app)

    def trio(self, url: str = '/', method: str = 'GET', **kwargs) -> Tuple[Request, Response, Context]:
        req = self.request(url, method, **kwargs)
        ctx = self.context()
        res = Response(self._app, ctx, req)
        return req, res, ctx

    # Short synonyms
    def req(self, *args, **kwargs): return self.request(*args, **kwargs)
    def res(self, *args, **kwargs): return self.response(*args, **kwargs)
    def ctx(self, *args, **kwargs): return self.context(*args, **kwargs)

    async def _simulate(self, method: str, url: str, body: Any = b'', headers: Dict = None) -> Tuple[Request, Response, Context]:
        final_headers = {**self._session_headers, **(headers or {})}
        
        if isinstance(body, (dict, list)):
            body = json.dumps(body).encode()
            final_headers.setdefault('content-type', 'application/json')
        elif isinstance(body, str):
            body = body.encode()
        
        # Prepare ASGI scope
        scope = {
            'type': 'http',
            'method': method,
            'path': url,
            'raw_path': url,
            'query_string': b'', # Improved below if needed
            'headers': _listify_headers(final_headers),
            'client': ('127.0.0.1', 8080),
            'scheme': 'http',
        }

        # Handle query string in URL
        if '?' in url:
            path, qs = url.split('?', 1)
            scope['path'] = path
            scope['raw_path'] = path
            scope['query_string'] = qs.encode()

        async def receive():
            return {'type': 'http.request', 'body': body, 'more_body': False}

        async def send(msg): pass

        engine = self._app.subdomains.get(DEFAULT)
        from .utils import preprocessor
        metadata = preprocessor(scope) 
        
        if not self._app._baked: self._app._bake_schemas()

        res = await engine.handle(scope, receive, send, metadata=metadata, application=self._app)
        
        # Session tracking (Simplified)
        if self._track_session:
            for k, v in res.headers:
                if k.decode().lower() == 'set-cookie':
                    # This is naive but works for simple testing
                    cookie_part = v.decode().split(';')[0]
                    if '=' in cookie_part:
                        name, val = cookie_part.split('=', 1)
                        self._session_cookies[name] = val
                        # Update session headers with Cookie header for next request
                        cookie_str = "; ".join([f"{n}={v}" for n, v in self._session_cookies.items()])
                        self._session_headers['cookie'] = cookie_str

        return res._req, res, res._ctx

    async def GET(self, url, **kwargs): return await self._simulate(GET, url, **kwargs)
    async def POST(self, url, **kwargs): return await self._simulate(POST, url, **kwargs)
    async def PUT(self, url, **kwargs): return await self._simulate(PUT, url, **kwargs)
    async def DELETE(self, url, **kwargs): return await self._simulate(DELETE, url, **kwargs)
    async def PATCH(self, url, **kwargs): return await self._simulate(PATCH, url, **kwargs)

    def test(self, track_session=True):
        return EarthContextManager(self, track_session)

class EarthContextManager:
    def __init__(self, earth: Earth, track_session: bool):
        self.earth = earth
        self.track_session = track_session
        self._original_initializers = []
        self._original_deinitializers = []

    async def __aenter__(self):
        self.earth._track_session = self.track_session
        
        # Intercept hooks
        if self.earth._swaps:
            from .router import _string_to_function_handler
            import functools

            def wrap_hook(hook, swaps):
                # Unwrap our own closure if it exists to get the original func
                original = getattr(hook, '__wrapped__', hook)
                replacement = swaps.get(original)
                if replacement:
                    if isinstance(replacement, str): replacement = _string_to_function_handler(replacement)
                    
                    @functools.wraps(replacement)
                    async def hidden(app):
                        from inspect import iscoroutinefunction
                        if iscoroutinefunction(replacement): return await replacement(app)
                        else: return replacement(app)
                    return hidden
                return hook

            # Backup and swap
            self._original_initializers = list(self.earth._app.initializers)
            self._original_deinitializers = list(self.earth._app.deinitializers)
            
            self.earth._app.initializers.clear()
            self.earth._app.initializers.extend([wrap_hook(h, self.earth._swaps) for h in self._original_initializers])
            
            self.earth._app.deinitializers.clear()
            self.earth._app.deinitializers.extend([wrap_hook(h, self.earth._swaps) for h in self._original_deinitializers])

        await self.earth._app._register()
        return self.earth

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Restore original hooks
        if self._original_initializers:
            self.earth._app.initializers.clear()
            self.earth._app.initializers.extend(self._original_initializers)
        if self._original_deinitializers:
            self.earth._app.deinitializers.clear()
            self.earth._app.deinitializers.extend(self._original_deinitializers)
            
        await self.earth._app._unregister()
