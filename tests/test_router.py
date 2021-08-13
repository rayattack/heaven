from collections import deque
from json import dumps
from typing import Callable
from unittest import TestCase, IsolatedAsyncioTestCase
from unittest.mock import Mock

from routerling import Router, ResponseWriter, HttpRequest, Context
from routerling.router import DEFAULT, Routes, _isparamx
from routerling.errors import SubdomainError, UrlDuplicateError, UrlError
from routerling.mocks import MOCK_SCOPE, MockHttpRequest, _get_mock_receiver

# internal test modules
from .test_request import one, two, three, four


MOCK_BODY = {'success': True}


def five(r: HttpRequest, w: ResponseWriter, c: Context):
    w.body = dumps({**r.body, 'message': 'five...'})


class AsyncRouterTet(IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.router = Router()
        self.scope = {**MOCK_SCOPE, 'path': '/v1/customers'}
        self.router.GET('/v1/customers', five)
        self.engine = self.router.subdomains.get('www')
        return super().setUp()
    
    async def test_handle(self):
        receiver = _get_mock_receiver('http.request', MOCK_BODY)
        metadata = 'www', None # i.e. subdomain and headers

        # scope host is ignored for subdomain routing because we are calling the engine directly
        response = await self.engine.handle(self.scope, receiver, None, metadata, self.router)
        self.assertIsInstance(response, ResponseWriter)

        expected_response_from_five = dumps({**MOCK_BODY, 'message': 'five...'}).encode()
        self.assertEqual(response.body, expected_response_from_five)
    
    async def test_call(self):
        async def send(data):
            return data
        receiver = _get_mock_receiver('http.request', MOCK_BODY)
        self.scope['headers'] = []
        result = await self.router(self.scope, receiver, send)


class RoutesTest(TestCase):
    def setUp(self) -> None:
        self.routes = Routes()
        self.router = Router()
        self.router.GET('/v1/customers/:id/receipts', one)
        self.router.GET('/v1/customers', three)
        self.engine = self.router.subdomains.get('www')
        return super().setUp()

    def test_add(self):
        self.assertRaises(UrlDuplicateError, self.engine.add, 'GET', '/v1/customers/:id/receipts', one)
        root_route_node = self.engine.routes.get('GET')
        self.assertIsNone(root_route_node.route)
        self.assertFalse(root_route_node.parameterized)

        v1_route_node = root_route_node.children.get('v1')
        self.assertIsNotNone(v1_route_node)
        self.assertIsNone(v1_route_node.route)
        self.assertIsNone(v1_route_node.handler)
        self.assertIsNone(v1_route_node.parameterized)

        customers_route_node = v1_route_node.children.get('customers')
        self.assertIsNotNone(customers_route_node)
        self.assertEqual(customers_route_node.route, '/v1/customers')
        self.assertEqual(customers_route_node.handler, three)
        self.assertIsNone(customers_route_node.parameterized)
    
        id_route_node = customers_route_node.children.get(':')
        self.assertIsNotNone(id_route_node)
        self.assertTrue(id_route_node.parameterized)
        self.assertEqual(id_route_node.parameterized, 'id')
        
        receipts_route_node = id_route_node.children.get('receipts')
        self.assertIsNotNone(receipts_route_node)
        self.assertEqual(receipts_route_node.handler, one)

    def test_routes_cache(self):
        self.assertIsNotNone(self.engine.cache['GET']['/v1/customers/:id/receipts'])

    def test_remove_handler(self):
        root_route_node = self.engine.routes.get('GET')
        v1_route_node = root_route_node.children.get('v1')
        customers_route_node = v1_route_node.children.get('customers')

        self.assertEqual(customers_route_node.handler, three)
        self.assertEqual(customers_route_node.route, '/v1/customers')

        self.engine.remove('GET', '/v1/customers')
        self.assertIsNone(customers_route_node.handler)
        self.assertIsNone(customers_route_node.route)
        self.assertFalse(self.engine.cache['GET']['/v1/customers'])
    
    def test_match(self):
        xsplit = lambda x: x.strip('/').split('/')

        # first match params
        url1 = '/v1/customers'
        url_q1 = deque(xsplit(url1))
        req1 = MockHttpRequest(url1)

        # second match params
        url2 = '/v1/customers/34/receipts'
        url_q2 = deque(xsplit(url2))
        req2 = MockHttpRequest(url2)

        # test first match params
        route, handler = self.engine.routes.get('GET').match(url_q1, req1)
        self.assertIsInstance(route, str)
        self.assertEqual(handler, three)

        # test second match params
        route, handler = self.engine.routes.get('GET').match(url_q2, req2)
        self.assertEqual(req2.params.get('id'), '34')
    
    def test_afters(self):
        self.router.AFTER('/v1/customers', three)
        afters = self.engine.afters.get('/v1/customers')
        self.assertIsInstance(afters, list)
        self.assertTrue(three in afters)
    
    def test_befores(self):
        self.router.BEFORE('/v1/customers', three)
        befores = self.engine.befores.get('/v1/customers')
        self.assertIsInstance(befores, list)
        self.assertTrue(three in befores)


class RouterTest(TestCase):
    def setUp(self) -> None:
        self.router = Router()
        return super().setUp()

    def test_required_leading_slash(self):
        bad_url = 'customers'
        placeholder = lambda r, w, c: print
        self.assertRaises(UrlError, self.router.GET, bad_url, placeholder)
        self.assertRaises(UrlError, self.router.POST, bad_url, placeholder)
        self.assertRaises(UrlError, self.router.DELETE, bad_url, placeholder)
        self.assertRaises(UrlError, self.router.PUT, bad_url, placeholder)
        self.assertRaises(UrlError, self.router.PATCH, bad_url, placeholder)
        self.assertRaises(UrlError, self.router.POST, '*', placeholder)

    def test_default_subdomain(self):
        self.assertEqual(list(self.router.subdomains.keys()), [DEFAULT])
    
    def test_subdomain_registration_required(self):
        self.assertRaises(SubdomainError, self.router.POST, '/customers', one, 'xui')
        self.router.subdomain('xui')
        self.router.POST('/customers', one, 'xui')
    
    def test_url_duplicate_error(self):
        self.router.POST('/customers', one)
        self.assertRaises(UrlDuplicateError, self.router.POST, '/customers', one)
    
    def test_subdomains(self):
        self.router.subdomain('api')
        self.router.subdomain('xui')
        self.router.POST('/customers', one, 'api')
        self.router.POST('/customers', one, 'xui')

        api_subdomain: Routes = self.router.subdomains.get('api')
        xui_subdomain: Routes = self.router.subdomains.get("xui")

        self.assertIsInstance(api_subdomain, Routes)
        self.assertIsInstance(xui_subdomain, Routes)

    def test_default_subdomain_engine(self):
        self.router.POST('/customers', one)
        self.router.POST('/:someone', two)
        self.router.POST('/v1/customers', three)
        self.router.POST('/v1/:someone/customers', one)
        self.assertIsInstance(self.router.subdomains.get(DEFAULT), Routes)

    def test_wildcard_route(self):
        self.router.POST('/*', one)

    def test_is_paramx(self):
        right = _isparamx(':ab')
        wrong = _isparamx('ab')
        self.assertIsInstance(right, tuple)
        self.assertEqual(right[0], ':')
        self.assertEqual(right[1], 'ab')
        self.assertEqual(wrong[0], 'ab')
        self.assertEqual(wrong[1], None)
