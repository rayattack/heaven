from datetime import datetime, timedelta

from json import dumps
from http import HTTPStatus as status
from mock import Mock, MagicMock
from unittest import TestCase

from heaven import Response, Router, Context
from heaven.constants import MESSAGE_NOT_FOUND
from heaven.response import _get_guardian_angel


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

def test_response_cookie_bad():
    try:
       response.cookie('authorization', 'Bearer 123', expires='2022-12-12', secure=False, SameSite='strict')
    except ValueError as e:
        assert str(e) == 'Expires must be a datetime object, got 2022-12-12'

def test_reasponse_cookie_good():
    response.cookie('authorization', 'Bearer 123', expires=datetime.now() + timedelta(days=1), secure=False, SameSite='strict')
    for header in response._headers:
        if header[0] == b'Set-Cookie':
            assert header[1].startswith(b'authorization=Bearer 123')

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


def test_response_headers():
    assert response.header('key', 'value') is not None


def test_response_body_encodings():
    response = Response(app=router, context=context)

    response.body = 'hello world'
    assert response.body == b'hello world'

    response.body = 4
    assert response.body == b'4'

def test_get_guardian_angel_html():
    res = Response(app=router, context=context)
    _get_guardian_angel(res, 'some error', 'some snippet')
    assert res.headers == [(b'Content-Type', b'text/html')]
    assert res.status == status.INTERNAL_SERVER_ERROR
    assert isinstance(res.body, bytes)


def test_response_redirect():
    res = Response(app=router, context=context)
    assert res.redirect('/some/path') is not None
    assert res.status == status.TEMPORARY_REDIRECT
    assert res.headers == [(b'Location', b'/some/path')]
