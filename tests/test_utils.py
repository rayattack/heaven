from unittest import TestCase

from routerling.constants import DEFAULT
from routerling.mocks import MOCK_SCOPE
from routerling.utils import b_or_s, preprocessor


class TestUtils(TestCase):
    def setUp(self) -> None:
        self.scope = {**MOCK_SCOPE}
        return super().setUp()

    def test_b_or_s(self):
        a, b = 'a str', b'a byte str'
        assert b_or_s(a) == a
        assert b_or_s(b) == 'a byte str'
    
    def test_scope(self):
        subdomain, headers = preprocessor(self.scope)
        self.assertEqual(subdomain, 'host')
    
    def test_scope_ip(self):
        self.scope['headers'] = [['host', '127.0.0.1']]
        subdomain, headers = preprocessor(self.scope)
        self.assertEqual(subdomain, DEFAULT)
        self.assertDictEqual(headers, {'host': '127.0.0.1'})
