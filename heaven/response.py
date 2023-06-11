from http import HTTPStatus
from os import path

from functools import singledispatch, update_wrapper
from http import HTTPStatus
from typing import TYPE_CHECKING

from .constants import MESSAGE_NOT_FOUND, STATUS_NOT_FOUND
from .context import Context
from .tutorials import get_guardian_angel_html, NO_TEMPLATING
if TYPE_CHECKING:
    from router import App


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


class Response():
    def __init__(self, app: 'App', context: 'Context'):
        self._app = app
        self._ctx = context
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

    def defer(self, func):
        self._deferred.append(func)

    @property
    def deferred(self):
        return len(self._deferred) > 0

    @property
    def headers(self):
        return self._headers

    @headers.setter
    def headers(self, value):
        key, val = value
        _encode = lambda k: k.encode('utf-8') if isinstance(k, str) else k
        value = _encode(key), _encode(val)
        self._headers.append(value)
    
    def file(self, name: str, folder='public'):
        """Serve file from assets/public folder with correct file type from known_file_types"""
        pass

    @property
    def metadata(self):
        return self._metadata

    @metadata.setter
    def metadata(self, value):
        if not isinstance(value, dict): raise ValueError
        self._metadata = value

    @property
    def mounted(self):
        return self._mounted_from_application

    @mounted.setter
    def mounted(self, value: 'App'):
        self._mounted_from_application = value

    async def render(self, name: str, **contexts):
        """Serve html file walking up parent router/app tree until base parent if necessary"""
        # TODO: add support to customize order in **contexts later when you think of the api and make an atomic commit
        templater = self.mounted._templater or self._app._templater
        if not templater:
            self.headers = 'Content-Type', 'text/html'
            self.status = HTTPStatus.INTERNAL_SERVER_ERROR
            self.body = get_guardian_angel_html('You did not enable templating', NO_TEMPLATING)
            return
        template = templater.get_template(name)
        self.body = await template.render_async({'ctx': self._ctx, **contexts})

    def renders(self, name: str):
        """Synchronous version of render method above"""
        pass

    def redirect(self, location, permanent=False):
        if permanent: self.status = HTTPStatus.PERMANENT_REDIRECT
        else: self.status = HTTPStatus.TEMPORARY_REDIRECT
        self.headers = 'Location', location

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, value: int):
        self._status = value

    @property
    def template(self):
        return self._template

    @template.setter
    def template(self, path):
        self._template
