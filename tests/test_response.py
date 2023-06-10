from json import dumps
from http import HTTPStatus as status
from unittest import TestCase

from heaven import Response, Router, Context
from heaven.constants import MESSAGE_NOT_FOUND


router = Router()
context = Context(router)
response = Response(app=router, context=context)


def test_headers_encoding():
    response.headers = 'content-type', 'application/json'
    response.headers = b'authorization', b'some-authorization-token'
    for _ in response._headers:
        k, v = _
        assert(isinstance(k, bytes) and isinstance(v, bytes))


def test_response_status():
    response.status = status.NOT_ACCEPTABLE
    assert(response.status == status.NOT_ACCEPTABLE)


def test_response_body():
    body = dumps({
        'title': 'yes ooo...'
    })
    message_not_found = MESSAGE_NOT_FOUND.encode('utf-8')
    assert(response.body == message_not_found)

    response.body = body
    _body = response._body
    assert(_body != message_not_found)
    assert(isinstance(_body, bytes))
