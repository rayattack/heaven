from typing import Any, TYPE_CHECKING

from routerling.form import Form


if TYPE_CHECKING:
    from routerling import Router


class HttpRequest:
    def __init__(self, scope, body, receive, metadata=None, application=None):
        self._application = application
        self._body = body
        self._cookies = None
        self._form = None
        self._receive = receive
        self._scope = scope
        self._subdomain, self._headers = metadata
        self._params = None

    def _parse_qs(self):
        qs = self._scope.get("query_string")
        qsd = {}
        if not qs:
            return qsd
        else:
            qs = qs.decode() if isinstance(qs, bytes) else qs

        query_kv_pairs = qs.split("&")
        for kv_pair in query_kv_pairs:
            key, value = kv_pair.split("=")
            current_value = qsd.get(key)
            if not current_value:
                qsd[key] = value
            else:
                if isinstance(current_value, list):
                    current_value.append(value)
                else:
                    qsd[key] = [current_value, value]
        return qsd

    @property
    def app(self) -> "Router":
        return self._application

    @property
    def body(self):
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
                k, v = cookie.split("=")
                csd[k] = v
            self._cookies = csd
        return self._cookies

    @property
    def form(self) -> "Form":
        if not "multipart/form-data" in self.headers.get("content-type"):
            return None  # currently none
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
                self._headers[header[0]] = header[1]
        return self._headers

    @property
    def method(self):
        return self._scope.get("method")

    @property
    def params(self):
        if not self._params:
            self._params = self._parse_qs()
        return self._params

    @params.setter
    def params(self, pair):
        if not self._params:
            self._params = {}
        self._params[pair[0]] = pair[1]

    @property
    def querystring(self):
        return self._scope.get("query_string", "")

    @property
    def scheme(self):
        return self._scope.get("scheme")

    @property
    def subdomain(self):
        return self._subdomain

    @property
    def url(self):
        return self._scope.get("path")

    async def stream(self):
        """TODO: Revisit and implement with appropriate testing"""
        return await self._receive()
