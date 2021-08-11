from unittest import TestCase

from routerling import Router
from routerling.router import DEFAULT, Routes
from routerling.errors import SubdomainError, UrlDuplicateError, UrlError
from routerling.response import ResponseWriter
from routerling.request import HttpRequest
from routerling.context import Context

# internal test modules
from .test_request import one, two, three


class RoutesTest(TestCase):
    def setUp(self) -> None:
        self.router = Router()
        return super().setUp()
    
    def test_add_handler(self):
        pass

    def test_remove_handler(self):
        pass


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

    def test_parameterized_route(self):
        # TODO: Implement test for this
        pass

    def test_function_matched_correctly_to_route(self):
        # TODO: Implement test for this
        pass
