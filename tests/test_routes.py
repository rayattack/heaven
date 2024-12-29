from collections import deque
from datetime import date, datetime
from uuid import UUID

from ujson import dumps, loads
from typing import Callable
from unittest import TestCase, IsolatedAsyncioTestCase
from unittest.mock import Mock, patch, AsyncMock, ANY, MagicMock

from heaven import App, Application, Router, Response, Request, Context
from heaven.router import DEFAULT, Routes, _isparamx, _notify, _get_configuration
from heaven.errors import SubdomainError, UrlDuplicateError, UrlError
from heaven.mocks import MOCK_SCOPE, MOCK_BODY, MockRequest, _get_mock_receiver

from tests import mock_scope


def five(r: Request, w: Response, c: Context):
    w.body = dumps({**loads(r.body), 'message': 'five...'})


class AsyncRouterTest(IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.routes = Routes()
        self.router = Router()
        self.app = App()

    def test_(self):
        pass

    async def test_duplicate_url(self):
        self.routes.add('POST', '/v1/customers/:id', lambda r, w, c:..., self.router)
        with self.assertRaises(UrlDuplicateError) as e:
            self.routes.add('POST', '/v1/customers/:id?age:int&expires:datetime', lambda r,w,c:..., self.router)

    async def test_route_queryhint(self):
        self.routes.add('POST', '/customers/:id?page:int&pagination:int&expires:datetime', lambda r,w,c:..., self.router)
        posts = self.routes.routes.get('POST')
        customer_route_object = posts.children.get('customers')
        self.assertIsNone(customer_route_object.handler)
        _route_object = customer_route_object.children.get(':')
        self.assertIsNotNone(_route_object)
        self.assertIsNotNone(_route_object.handler)
        self.assertEqual(_route_object.queryhint, 'page:int&pagination:int&expires:datetime')

    async def test_route_handler_called(self):
        async def receive(): return {}
        async def send(data): pass
        mocked = MagicMock()
        self.app.GET('/customers/:id/orders?page:int&pagination:int', mocked)
        await self.app(mock_scope, receive, send)

        # self.assertEqual(self.request.qh, 'page:int&pagination:int')
        mocked.assert_called_once()

    async def test_query_hint_parsing(self):
        qs = 'page=5&price=53.14&catalog=27261936-1407-415b-99f5-9e06a006640e&expires=2024-12-27T01:07:38.034213&log=2024-12-27&prio=TrUe'
        suffix = 'page:int&price:float&catalog:uuid&expires:datetime&log:date&prio:bool'
        scope = dict({**mock_scope})
        scope['query_string'] = qs
        async def receive(): return {}
        async def send(data): pass
        async def handler(req, res, ctx):
            assert isinstance(req.queries.get('page'), int)
            assert isinstance(req.queries.get('price'), float)
            assert isinstance(req.queries.get('expires'), datetime)
            assert isinstance(req.queries.get('log'), date)
            assert isinstance(req.queries.get('catalog'), UUID)
            assert isinstance(req.queries.get('prio'), bool)
            assert req.queries.get('prio') == True
        self.app.GET(f'/customers/:id/orders?{suffix}', handler)
        await self.app(scope, receive, send)

    async def test_query_hint_present(self):
        async def receive(): return {}
        async def send(data): pass
        queryhint = 'page:int&pagination:int'
        async def handler(req, res, ctx):
            assert req.qh == queryhint
        self.app.GET('/customers/:id/orders?page:int&pagination:int', handler)
        engines = self.app.subdomains['www']
        self.assertIsInstance(engines, Routes)
        gets = engines.routes.get('GET')
        customer_route = gets.children.get('customers')
        self.assertIsNotNone(customer_route)
        _route = customer_route.children.get(':')
        self.assertIsNotNone(_route)
        orders_route = _route.children.get('orders')
        self.assertEqual(orders_route.queryhint, queryhint)
        self.assertIsNotNone(orders_route)
        self.assertEqual(orders_route.handler, handler)
        await self.app(mock_scope, receive, send)

