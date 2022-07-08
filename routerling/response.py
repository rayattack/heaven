from functools import singledispatch, update_wrapper

from .constants import MESSAGE_NOT_FOUND, STATUS_NOT_FOUND


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


class ResponseWriter():
    def __init__(self):
        self._abort = False
        self._body = MESSAGE_NOT_FOUND.encode()
        self._metadata = {}
        self._headers = []
        self._status = STATUS_NOT_FOUND

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
    
    @property
    def headers(self):
        return self._headers

    @headers.setter
    def headers(self, value):
        key, val = value
        _encode = lambda k: k.encode('utf-8') if isinstance(k, str) else k
        value = _encode(key), _encode(val)
        self._headers.append(value)
    
    @property
    def metadata(self):
        return self._metadata
    
    @metadata.setter
    def metadata(self, value):
        if not isinstance(value, dict): raise ValueError
        self._metadata = value

    @property
    def status(self):
        return self._status
    
    @status.setter
    def status(self, value: int):
        self._status = value
