import unittest
from heaven.request import Request

class TestQueryString(unittest.TestCase):
    def test_url_decoding_missing(self):
        scope = {
            'type': 'http',
            'query_string': b'name=John%20Doe&email=john%40example.com'
        }
        request = Request(scope, b'', None, (None, {}))
        queries = request.queries
        
        # This will likely fail in the current implementation
        self.assertEqual(queries.get('name'), 'John Doe')
        self.assertEqual(queries.get('email'), 'john@example.com')

    def test_values_with_equals_sign(self):
        scope = {
            'type': 'http',
            'query_string': b'data=a=b=c'
        }
        request = Request(scope, b'', None, (None, {}))
        queries = request.queries
        
        # This will likely fail because it tries to split into exactly 2 parts
        self.assertEqual(queries.get('data'), 'a=b=c')
    def test_query_hint_coercion(self):
        from uuid import UUID
        scope = {
            'type': 'http',
            'query_string': b'id=123&price=19.99&uid=550e8400-e29b-41d4-a716-446655440000'
        }
        request = Request(scope, b'', None, (None, {}))
        
        # Set query hints
        request.qh = "id:int&price:float&uid:uuid"
        
        queries = request.queries
        self.assertEqual(queries.get('id'), 123)
        self.assertIsInstance(queries.get('id'), int)
        self.assertEqual(queries.get('price'), 19.99)
        self.assertIsInstance(queries.get('price'), float)
        self.assertEqual(queries.get('uid'), UUID('550e8400-e29b-41d4-a716-446655440000'))
        self.assertIsInstance(queries.get('uid'), UUID)

if __name__ == '__main__':
    unittest.main()
