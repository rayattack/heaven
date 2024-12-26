from json import dumps, load
from unittest import TestCase
from unittest.case import skip
from unittest.mock import MagicMock

from heaven import App, Application, Router
from heaven import Request, Response, Context
from heaven.utils import preprocessor


from tests import mock_scope, mock_body, mock_receive, mock_metadata


def one(r: Request, w: Response, c: Context):
    """Response should be tested in response class but setup of body done here"""
    w.body = 1000


def two(r: Request, w: Response, c: Context):
    w.body = 2000


def three(r: Request, w: Response, c: Context):
    w.body = 3000


def four(r: Request, w: Response, c: Context):
    w.body = 4000


class TestRequest(TestCase):
    def setUp(self) -> None:
        self.app = App()
        self.request = Request(
            mock_scope, mock_body, mock_receive, mock_metadata, self.app
        )
        return super().setUp()

    def test_request_app_instance(self):
        self.assertIsInstance(self.request.app, Router)

    def test_request_body(self):
        self.assertEqual(self.request.body, mock_body)

    def test_request_cookies(self):
        self.assertIsNotNone(self.request.cookies)
        self.assertEqual(self.request.cookies.get("foo"), "bar")
        self.assertEqual(self.request.cookies.get("baz"), "yimu")

    def test_preprocessor(self):
        results = preprocessor(mock_scope)
        self.assertIsInstance(results, tuple)
        subdomain, headers = results
        self.assertIsInstance(subdomain, str)
        self.assertIsInstance(headers, dict)

        self.assertEqual(subdomain, "host")

    def test_headers_preprocessed(self):
        self.assertIsInstance(self.request.headers.get("set-cookie"), list)

        # tied to content of asgi.json so change that file with care
        cookie_message = "i added this for testing manually and not from scope object"
        self.assertEqual(self.request.headers.get("set-cookie")[0], cookie_message)

        # remove preprocessed headers forcefully (i.e. ignoring private hint in var name)
        self.request._headers = None
        self.assertIsInstance(self.request.headers, dict)

    def test_params_setting_appropriately(self):
        self.request.params = "key", "value"
        self.request.params = "another", True
        self.assertEqual(self.request.params.get("key"), "value")

        self.request._scope = {}
        self.request._params = None
        self.assertDictEqual(self.request.params, {})

    def test_params_coerce_data_type(self):
        self.request.params = "age:int", "4"
        self.request.params = "name:str", "Yeshua"
        self.assertIsInstance(self.request.params.get('age'), int)
        self.assertEqual(self.request.params.get('age'), 4)
        self.assertEqual(self.request.params.get('name'), 'Yeshua')

    def test_query_strings_parsed_correctly(self):
        queries = self.request.queries
        self.assertEqual(queries.get("page"), "2")
        self.assertIsInstance(queries.get("pagination"), list)
    
    def test_querystring_helper(self):
        self.assertIsNotNone(self.request.querystring)

    def test_request_method_parsed_from_scope(self):
        self.assertEqual(self.request.method, "GET")

    def test_request_scheme(self):
        self.assertEqual(self.request.scheme, "http")

    def test_subdomain(self):
        self.assertEqual(self.request.subdomain, "host")

    def test_request_path_retrieval(self):
        return self.assertEqual(self.request.url, "/customers/23/orders")

    @skip
    def test_stream(self):
        stream = self.request.stream()
