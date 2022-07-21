from .context import Context
from .request import HttpRequest
from .response import ResponseWriter

from .constants import METHODS


MOCK_SCOPE = {
    "type": "http",
    "asgi": {
        "version": "3.0",
        "spec_version": "2.1"
    },
    "http_version": "1.1",
    "server": ["127.0.0.1", 8000],
    "client": ["127.0.0.1", 56467],
    "scheme": "http",
    "method": "GET",
    "root_path": "",
    "path": "/customers/23/orders",
    "raw_path": "/customers/23/orders",
    "query_string": "page=2&pagination=50&pagination=75",
    "headers": [
        ["host", "host.localdomain.localhost:8000"],
        ["connection", "keep-alive"],
        ["cache-control", "max-age=0"],
        ["sec-ch-ua", "'Google Chrome';v='89', 'Chromium';v='89', ';Not A Brand';v='99'"],
        ["sec-ch-ua-mobile", "?0"],
        ["upgrade-insecure-requests", "1"],
        ["user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.72 Safari/537.36"],
        ["accept", "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9"],
        ["sec-fetch-site", "none"],
        ["sec-fetch-mode", "navigate"],
        ["sec-fetch-user", "?1"],
        ["sec-fetch-dest", "document"],
        ["accept-encoding", "gzip, deflate, br"],
        ["accept-language", "en-US,en;q=0.9"],
        ["set-cookie", "i added this for testing manually and not from scope object"],
        ["set-cookie", "according to the standard i read set-cookie can appear twice"]
    ]
}
MOCK_BODY = {
    'type': 'http.request.body',
    'body': b'{"example": "Some JSON data"}',
    'more_body': False
}



def _get_mock_receiver():
    async def receive():
        return MOCK_BODY
    return receive


def _listify_headers(headers: dict):
    if not headers: return []
    temp = []
    for k, v in headers.items():
        if isinstance(v, list):
            for i in v: temp.append([k, i])
        else: temp.append([k, v])
    return temp


class MockContext(Context):
    def __init__(self, payload, application=None):
        super().__init__(application)
        self._data = payload


class MockHttpRequest(HttpRequest):
    def __init__(
        self,
        url,
        body='',
        method='GET',
        host='localhost',
        query_string='',
        headers=None,
        subdomain='www',
        event='http.request',
        scope={**MOCK_SCOPE}
    ):
        assert method in METHODS
        receive = _get_mock_receiver()
        scope['path'] = url
        scope['raw_path'] = url
        scope['method'] = method
        scope['headers'] = _listify_headers(headers)
        scope['query_string'] = query_string
        metadata = subdomain, headers or {}
        super().__init__(scope, body, receive, metadata=metadata)


class MockResponseWriter(ResponseWriter):
    def __init__(self):
        super().__init__()
