from collections import deque
from json import dumps
from typing import Callable
from unittest import TestCase, IsolatedAsyncioTestCase
from unittest.mock import Mock, patch, AsyncMock, ANY

from routerling import Router, ResponseWriter, HttpRequest, Context
from routerling.router import DEFAULT, Routes, _isparamx, _notify, _get_configuration
from routerling.errors import SubdomainError, UrlDuplicateError, UrlError
from routerling.mocks import MOCK_SCOPE, MockHttpRequest, _get_mock_receiver

# internal test modules
from tests import mock_scope, mock_receive, mock_metadata
from tests.test_request import one, two, three, four


MOCK_BODY = {'success': True}
MOCK_BODY_EXPECTED = {**MOCK_BODY, 'message': 'five...'}


def five(r: HttpRequest, w: ResponseWriter, c: Context):
    w.body = dumps({**r.body, 'message': 'five...'})


class AsyncRouterTest(IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.router = Router()
        self.scope = {**MOCK_SCOPE, 'path': '/v1/customers'}
        self.router.GET('/v1/customers', five)
        self.engine = self.router.subdomains.get(DEFAULT)
        return super().setUp()
    
    async def test_handle(self):
        receiver = _get_mock_receiver('http.request', MOCK_BODY)
        metadata = DEFAULT, None # i.e. subdomain and headers

        # scope host is ignored for subdomain routing because we are calling the engine directly
        response = await self.engine.handle(self.scope, receiver, None, metadata, self.router)
        self.assertIsInstance(response, ResponseWriter)

        expected_response_from_five = dumps(MOCK_BODY_EXPECTED).encode()
        self.assertEqual(response.body, expected_response_from_five)
    
    @patch('routerling.router._notify')
    async def test_call(self, _notify):
        mock = Mock()

        async def send(data): return mock(data)
        def exception_raiser(): raise Exception

        self.router.ONCE(exception_raiser)

        receiver = _get_mock_receiver('http.request', MOCK_BODY)
        self.scope['headers'] = []
        result = await self.router(self.scope, receiver, send)
        # lifespan event requires additional mocking so comment and notify tested in own function below already... self.assertEqual(mock.call_count, 2)
        expected_response = dumps(MOCK_BODY_EXPECTED).encode()
        mock.assert_called_with({'type': 'http.response.body', 'body': expected_response})
    
    async def test_once(self):
        self.assertRaises(TypeError, self.router.ONCE, 'blah')
        self.assertRaises(ValueError, self.router.ONCE, lambda x: x, 'blah')
        self.router.ONCE(lambda x: x)

        self.assertEqual(len(self.router.initializers), 1)
    
    async def test_register(self):
        a, b, c = Mock(), Mock(), Mock()
        a.__name__ = 'a'
        b.__name__ = 'b'
        c.__name__ = 'c'
        self.router.ONCE('startup', a)
        self.router.ONCE('startup', b)
        self.router.ONCE(c)

        self.assertEqual(len(self.router.initializers), 3)
        self.assertRaises(TypeError, self.router.ONCE, 'shutdown', 'blah')

        # now call finalize multiple times
        await self.router._register()
        await self.router._register()
        await self.router._register()

        # ensure one time functions were only called once
        a.assert_called_once()
        b.assert_called_once()
        c.assert_called_once()
    
    async def test_unregister(self):
        a, b = Mock(), Mock()
        a.__name__ = 'a'
        b.__name__ = 'b'

        self.router.ONCE('shutdown', a)
        self.router.ONCE('shutdown', b)

        self.assertEqual(len(self.router.deinitializers), 2)
        
        await self.router._unregister()
        await self.router._unregister()

        a.assert_called_once()
        b.assert_called_once()
    
    async def test_mount(self):
        router_a = Router({'SECRET': 'one', 'ID': 100})
        router_b = Router({'SECRET': 'two'})
        router_c = Router({'SECRET': 'three'})

        router = Router()
        router.mount(router_c, isolated=False)
        router.mount(router_b)

        # All other routers were isolated so they will not override secret from C
        self.assertEqual('three', router.CONFIG('SECRET'))

        router.mount(router_a, isolated=False)
        self.assertEqual(100, router.CONFIG('ID'))
    
    async def test_mount_isolation(self):
        URL = '/customers/:id/orders'

        msend = AsyncMock()
        async def mrecv():...

        async def isolated_handler(r, w, c):
            self.assertEqual('aye', r.app.CONFIG('SECRET'))
            self.assertEqual('Router A', r.app.peek('name'))
        
        def unisolated_handler(r, w, c):
            self.assertIsNone(r.app.CONFIG('SECRET'))
            self.assertEqual('Default Router', r.app.peek('name'))

        #isolated mount
        router_a = Router({'SECRET': 'aye', 'ID': 100})
        router_a.subdomain('host')
        router_a.keep('name', 'Router A')
        router_a.GET(URL, isolated_handler, 'host')

        router = Router({'SECRET': None})
        router.keep('name', 'Default Router')
        router.mount(router_a)
        await router(mock_scope, mrecv, msend)

        # unisolated mount
        router_b = Router({'SECRET': 'bee', 'ID': 100})
        router_b.subdomain('host')
        router_b.keep('name', 'Router A')
        router_b.GET(URL, unisolated_handler, 'host')

        router = Router({'SECRET': None})
        router.keep('name', 'Default Router')
        router.mount(router_b, isolated=False)
        await router(mock_scope, mrecv, msend)

        msend.assert_called()


class RoutesTest(TestCase):
    def setUp(self) -> None:
        self.routes = Routes()
        self.router = Router({'DB': 'arangodb'})
        self.router.GET('/v1/customers/:id/receipts', one)
        self.router.GET('/v1/customers', three)
        self.router.GET('/v1/customers/*', four)
        self.router.GET('/', four)
        self.engine = self.router.subdomains.get(DEFAULT)
        return super().setUp()

    def test_add(self):
        self.assertRaises(UrlDuplicateError, self.engine.add, 'GET', '/v1/customers/:id/receipts', one, self.router)
        root_route_node = self.engine.routes.get('GET')
        self.assertEqual(root_route_node.handler, four)
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

        # second match params
        url3 = '/v1/customers/34/receipts/45'
        url_q3 = deque(xsplit(url3))
        req3 = MockHttpRequest(url3)

        # test first match params
        route, handler = self.engine.routes.get('GET').match(url_q1, req1)
        self.assertIsInstance(route, str)
        self.assertEqual(handler, three)

        # test second match params
        route, handler = self.engine.routes.get('GET').match(url_q2, req2)
        self.assertEqual(req2.params.get('id'), '34')

        # test third match params
        route, handler = self.engine.routes.get('GET').match(url_q3, req3)
        self.assertEqual(route, '/v1/customers/*')
        self.assertEqual(handler, four)
    
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
        self.router = Router({'DB': 'arangodb'})
        self.engine = self.router.subdomains.get(DEFAULT)
        return super().setUp()
    
    def test_configurator_parser(self):
        _config = {'DBNAME': 'postgres', 'SECRET_KEY': 'something hard to guess and not english'}
        _configurator = lambda: {**_config, 'EXTRA': 'added in func configurator'}
        self.assertEqual(_get_configuration(_config), _config)
        self.assertEqual(_get_configuration(), {})
        self.assertEqual('added in func configurator', _configurator()['EXTRA'])

        self.assertEqual(self.router.CONFIG('DB'), 'arangodb')
        self.assertRaises(KeyError, Router().CONFIG, 'DB')

    def test_keep(self):
        self.router.keep('bucket', 100)
        self.assertEqual(self.router.peek('bucket'), 100)
        self.assertEqual(self.router.unkeep('bucket'), 100)
        self.assertRaises(KeyError, self.router.unkeep, 'bucket')
    
    def test_peek(self):
        self.assertIsNone(self.router.peek('blah'))
        self.router.keep('blah', 'yimu')
        self.assertEqual(self.router.peek('blah'), 'yimu')
        self.assertEqual(self.router.peek('blah'), 'yimu')
        self.assertEqual(self.router.unkeep('blah'), 'yimu')
        self.assertIsNone(self.router.peek('blah'))

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
    
    def test_methods(self):
        self.router.GET('/get', one)
        self.router.DELETE('/delete', one)
        self.router.TRACE('/trace', one)
        self.router.PUT('/put', one)
        self.router.POST('/post', one)
        self.router.PATCH('/patch', one)
        self.router.OPTIONS('/options', one)
        self.router.CONNECT('/connect', one)
        self.router.HTTP('/round-robin', one)
        for method in ['GET', 'PUT', 'PATCH', 'POST', 'DELETE', 'TRACE', 'OPTIONS']:
            self.assertIsNotNone(self.engine.routes.get(method))
            self.assertIsNotNone(self.engine.cache[method]['/round-robin'])
