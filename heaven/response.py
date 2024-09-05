from http import HTTPStatus
from os import path

from functools import singledispatch, update_wrapper
from http import HTTPStatus
from typing import TYPE_CHECKING

from .constants import MESSAGE_NOT_FOUND, STATUS_NOT_FOUND
from .context import Context
from .tutorials import get_guardian_angel_html, ASYNC_RENDER, NO_TEMPLATING, SYNC_RENDER
from .request import Request
if TYPE_CHECKING:
    from router import App  # pragma: no cover


# For compatibility with older versions of python3 using this
# otherwise would use singledispatchmethod available from ^3.8
def MethodDispatch(method):
    decorated = singledispatch(method)
    def decorator(*args, **kwargs):
        return decorated.dispatch(args[1].__class__)(*args, **kwargs)
    decorator.register = decorated.register
    update_wrapper(decorator, method)
    return decorator


@singledispatch
def _body(payload):
    return payload

@_body.register(str)
def _(payload: str):
    return payload.encode()

@_body.register(int)
@_body.register(float)
def _(payload):
    return f'{payload}'.encode()

def _get_guardian_angel(res: 'Response', error: str, snippet: str):
    res.headers = 'Content-Type', 'text/html'
    res.status = HTTPStatus.INTERNAL_SERVER_ERROR
    res.body = get_guardian_angel_html(error, snippet)


class Response():
    def __init__(self, app: 'App', context: 'Context', request: Request):
        self._app = app
        self._ctx = context
        self._req = request
        self._abort = False
        self._body = MESSAGE_NOT_FOUND.encode()
        self._deferred = []
        self._metadata = {}
        self._headers = []
        self._status = STATUS_NOT_FOUND
        self._template = None
        self._mounted_from_application = None

    @MethodDispatch
    def abort(self, payload):
        self._abort = True
        self._body = payload

    @abort.register(str)
    def _(self, payload: str):
        self._abort = True
        self._body = payload.encode()

    @abort.register(int)
    @abort.register(float)
    def _(self, payload):
        self._abort = True
        self._body = f'{payload}'.encode()

    @property
    def body(self):
        return self._body

    @body.setter
    def body(self, value):
        self._body = _body(value)

    def defer(self, func) -> 'Response':
        self._deferred.append(func)
        return self

    @property
    def deferred(self):
        return len(self._deferred) > 0

    def header(self, key, val) -> 'Response':
        _encode = lambda k: k.encode('utf-8') if isinstance(k, str) else k
        value = _encode(key), _encode(val)
        self._headers.append(value)
        return self

    @property
    def headers(self):
        return self._headers

    @headers.setter
    def headers(self, value) -> 'Response':
        key, val = value
        return self.header(key, val)

    @property
    def metadata(self):
        return self._metadata

    @metadata.setter
    def metadata(self, value):
        if not isinstance(value, dict): raise ValueError
        self._metadata = value

    def cookie(self, name: str, value: str, **kwargs):
        cookie_string = f'{name}={value}'
        for key, val in kwargs.items():
            _key = {
                'expires': 'Expires',
                'secure': 'Secure',
                'httponly': 'HttpOnly',
                'http_only': 'HttpOnly',
                'samesite': 'SameSite',
                'same_site': 'SameSite',
                'domain': 'Domain',
                'path': 'Path',
                'partitioned': 'Partitioned',
                'max_age': 'Max-Age',
                'maxage': 'Max-Age',
            }.get(key.lower(), key)
            if _key == 'Expires':
                try: val = val.strftime('%a, %d %b %Y %H:%M:%S GMT')
                except: raise ValueError(f'Expires must be a datetime object, got {val}')
            if _key in ['Secure', 'HttpOnly', 'Partitioned']:
                if val: cookie_string += f'; {_key}'
                continue
            if _key == 'Max-Age':
                try: val = int(val)
                except: raise ValueError(f'Max-Age must be an integer, got {val}')
            if _key == 'SameSite':
                _val = str(val).capitalize()
                if _val not in ['Strict', 'Lax', 'None']:
                    raise ValueError(f'SameSite must be one of Strict, Lax, None, got {val}')
                val = _val
            cookie_string += f'; {_key}={val}'
        self.headers = 'Set-Cookie', f'{name}={value}'

    async def render(self, name: str, **contexts) -> 'Response':
        """Serve html file walking up parent router/app tree until base parent if necessary"""
        templater = self._app._templater
        self.headers = 'content-type', 'text/html; charset=utf-8'
        # if self._mounted_from_application: templater = self._mounted_from_application._templater or templater
        if not templater:
            return _get_guardian_angel(self, 'You did not enable templating', NO_TEMPLATING)

        if not templater.is_async:
            return _get_guardian_angel(self, 'Trying to use Sync HTML Renderer to render HTML Async', ASYNC_RENDER)

        template = templater.get_template(name)
        self.body = await template.render_async({'ctx': self._ctx, 'res': self, 'req': self._req, **contexts})
        return self

    def renders(self, name: str, **contexts) -> 'Response':
        """Synchronous version of render method above"""
        templater = self._app._templater
        self.headers = 'content-type', 'text/html; charset=utf-8'
        if not templater:
            return _get_guardian_angel(self, 'You did not enable templating', NO_TEMPLATING)

        if templater.is_async:
            return _get_guardian_angel(self, 'Trying to use Async HTML Renderer to render Sync HTML', SYNC_RENDER)
        template = templater.get_template(name)
        self.body = template.render({'ctx': self._ctx, 'res': self, 'req': self._req, **contexts})
        return self

    def redirect(self, location, permanent=False) -> 'Response':
        if permanent: self.status = HTTPStatus.PERMANENT_REDIRECT
        else: self.status = HTTPStatus.TEMPORARY_REDIRECT
        self.headers = 'Location', location
        return self

    @property
    def status(self): # pragma: no cover
        return self._status

    @status.setter
    def status(self, value: int) -> 'Response':
        self._status = value
        return self

    @property
    def template(self):  # pragma: no cover
        return self._template

    @template.setter
    def template(self, path):
        self._template

    def out(self, status: int, body, headers=None) -> 'Response':
        self.status = status
        self.body = body
        if headers: self.headers = headers
        return self

    async def interpolate(self, name: str, **contexts):
        """Serve html file walking up parent router/app tree until base parent if necessary"""
        templater = self._app._templater
        if not templater: raise AttributeError('Can not interpolate without enabling templating on the heaven application')
        if not templater.is_async: raise AttributeError('Async rendering not supported by sync renderer')
        template = templater.get_template(name)
        return await template.render_async({'ctx': self._ctx, **contexts})
