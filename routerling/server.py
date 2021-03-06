request_interface = {
    "type": "http.request",
    "body": b"{'json': true}",
    "more_body": False,
}

async def application(scope, request, response):
    event = await request()
    ...
    # await response({"type": "websocket.send", "text": "Why hello there..."})
    await response({'type': 'http.response.start', 'status': 200, 'headers': [b'content-type', b'text/plain']})
    await response({'type': 'http.response.body', 'body': b'Why hello there...'})


class Server:
    def __call__(self, *args: Any, **kwds: Any) -> Any:
        pass
