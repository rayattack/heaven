from typing import Any, TYPE_CHECKING, Union, TypeVar, Generic
from urllib.parse import parse_qs

from heaven.form import Form
from heaven.utils import CONVERTERS, Lookup, boolean
from orjson import dumps, loads
from pytastic import Pytastic


if TYPE_CHECKING:
    from heaven import Router

T = TypeVar("T")

class Request(Generic[T]):
    def __init__(self, scope, body, receive, metadata=None, application=None):
        self._application = application
        self._body = body
        self._cookies = None
        self._form = None
        self._route = None
        self._receive = receive
        self.__qh = {}
        self.__queryhint = ''
        self._scope = scope
        self._subdomain, self._headers = metadata
        self._params = None
        self._queries = None
        self._data = None
        self._schema = None
        self._dirty = False
        self._queried = False
        self._mounted_from_application = None
        self._streaming = False
        self._streamed = False

    @property
    def json(self):
        """Returns the json body of the request"""
        body = self.body
        if not body: return None
        return loads(body)

    @property
    def data(self) -> T:
        """Returns the validated data from the request body as per schema definition"""
        if self._data is not None: return self._data
        if not self._body: return None  # type: ignore
        
        # If no schema was provided, behavior is same as req.json
        if not self._schema: return self.json
        
        # Use the app's shared pytastic instance if available
        if self.app and hasattr(self.app, '_pytastic'):
            self._data = self.app._pytastic.validate(self._schema, self.json)
        else: self._data = Pytastic().validate(self._schema, self.json)
        return self._data

    def _parse_qs(self):
        qs = self._scope.get("query_string", b"")
        if isinstance(qs, bytes):
            qs = qs.decode()
        
        parsed = parse_qs(qs, keep_blank_values=True)
        qsd = {}
        
        for key, values in parsed.items():
            coercion = self.__qh.get(key)
            processed_values = []
            for value in values:
                if coercion:
                    try: value = coercion(value)
                    except: pass
                processed_values.append(value)
            
            if len(processed_values) == 1:
                qsd[key] = processed_values[0]
            else:
                qsd[key] = processed_values
        return qsd

    @property
    def app(self) -> "Router":
        return self._application

    @property
    def body(self):
        if self._streaming:
            raise RuntimeError(
                'This route was registered with stream=True so its body was never '
                'buffered. Read it with `async for chunk in req.stream():` instead.'
            )
        return self._body

    @property
    def cookies(self):
        if not self._cookies:
            csd = {}
            cookiestring = self.headers.get("cookie")
            if not cookiestring:
                self._cookies = csd
                return self._cookies
            cookies = cookiestring.split("; ")
            for cookie in cookies:
                try: k, v = cookie.split("=", 1)
                except: pass
                else: csd[k] = v
            self._cookies = csd
        return self._cookies

    @property
    def form(self) -> Union["Form", None]:
        """The parsed form, or None when the request has no form content type.
        On a route registered with stream=True nothing is buffered ahead of the
        handler, so the form starts unparsed: get it with `form = await req.form`,
        which reads the body incrementally and spills large file parts to disk.
        Awaiting is harmless on a buffered route, where the form is parsed already.
        """
        content_type = self.headers.get("content-type", "")
        if not ("multipart/form-data" in content_type or "application/x-www-form-urlencoded" in content_type):
            return None
        if self._form is None:
            form = Form(self)
            self._form = form
            return form
        return self._form

    @property
    def headers(self):
        if not self._headers:
            self._headers = {}
            for header in self._scope.get("headers"):
                key = header[0].decode() if isinstance(header[0], bytes) else header[0]
                value = header[1].decode() if isinstance(header[1], bytes) else header[1]
                self._headers[key] = value
        return self._headers

    @property
    def host(self):
        return self.headers.get('host')
    
    @property
    def ip(self):
        address, port = self._scope.get("client")
        return Lookup({'address': address, 'port': port})

    @property
    def qh(self) -> str:
        return self.__queryhint

    @qh.setter
    def qh(self, val: str):
        '''Here we process queryhints so heaven can try to coerce query string values'''
        if self.__queryhint: raise ValueError('Querystring metadata already set')

        # Query values keep their historical lenient boolean, where an unreadable
        # value reads as False. Route segments use the strict parse from CONVERTERS
        # because there a failure means the route simply does not match.
        def lenient_boolean(v: str) -> bool:
            try: return boolean(v)
            except ValueError: return False

        kinds = {**CONVERTERS, 'bool': lenient_boolean}
        for pair in val.split('&'):
            try: k, v = pair.split(':')
            except: continue
            kind = kinds.get(v)
            if kind: self.__qh[k] = kind
        self.__queryhint = val

    @property
    def route(self):
        return self._route

    @property
    def scheme(self):
        return self._scope.get("scheme")

    @property
    def server(self) -> str:
        server = self._scope.get('server')
        return f'{server[0]}:{server[1]}'

    @property
    def method(self):
        return self._scope.get("method")

    @property
    def mounted(self):
        return self._mounted_from_application

    @mounted.setter
    def mounted(self, value: 'Router'):
        self._mounted_from_application

    @property
    def params(self) -> dict:
        if not self._dirty:
            if not self._params: self._params = {}
            self._params = {**self._params}
            self._dirty = True
        return self._params or {}

    @params.setter
    def params(self, pair):
        if not self._params:
            self._params = {}
        key, value = pair
        self._params[key] = value

    @property
    def queries(self):
        if not self._queried:
            if not self._queries: self._queries = {}
            self._queries = {**self._parse_qs()}
            self._queried = True
        return self._queries or {}

    @queries.setter
    def queries(self, pair):
        if not self._queries:
            self._queries = {}
        self._queries[pair[0]] = pair[1]

    @property
    def querystring(self):
        return self._scope.get("query_string", "")

    @property
    def subdomain(self):
        return self._subdomain

    @property
    def url(self):
        return self._scope.get("path")

    async def stream(self):
        """Yield the request body chunk by chunk, so a large upload never has to sit
        in memory. Available on routes registered with `stream=True`; on any other
        route the body has already been read and is waiting on `req.body`.

            app.POST('/upload', save, stream=True)

            async def save(req, res, ctx):
                async with async_open(target, 'wb') as f:
                    async for chunk in req.stream():
                        await f.write(chunk)

        The body arrives once and is not retained, so it can only be streamed once.
        """
        if not self._streaming:
            raise RuntimeError(
                'Register this route with stream=True to read its body as a stream. '
                'Without it the body is buffered already and available as req.body.'
            )
        if self._streamed:
            raise RuntimeError('The request body has already been streamed')
        self._streamed = True

        more = True
        while more:
            message = await self._receive()
            chunk = message.get('body', b'')
            if chunk: yield chunk
            more = message.get('more_body', False)

