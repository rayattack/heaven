from unittest import TestCase

from routerling.mocks import _listify_headers
from routerling.mocks import MockHttpRequest, MockResponseWriter, MockContext


class TestMocks(TestCase):
    def setUp(self) -> None:
        self.http_request = MockHttpRequest('/v1/customers', host='https://api.someone.com')
        self.context = MockContext({'key': 'value'})
        self.response_writer = MockResponseWriter()
        return super().setUp()
    
    def test_listify_headers(self):
        ad = {'a': True, 'b': 5, 'c': None, 'set-cookie': ['yes', 'no', 'maybe']}
        listified_headers = _listify_headers(ad)
        self.assertTrue(['a', True] in listified_headers)
        self.assertTrue(['set-cookie', 'yes'] in listified_headers)
        self.assertTrue(['set-cookie', 'no'] in listified_headers)
        self.assertTrue(['set-cookie', 'maybe'] in listified_headers)
        self.assertEqual(len(listified_headers), 6)

    def test_mock_context(self):
        self.assertEqual(self.context.key, 'value')

    def test_mocks_http_request(self):
        self.assertDictEqual(self.http_request.headers, {})
    
    def test_raises_assertion_error(self):
        self.assertRaises(AssertionError, MockHttpRequest, '/', method='RUBBISH')
