import unittest
from heaven.request import Request
from heaven.form import Form

class TestForm(unittest.TestCase):
    def test_multipart_form_parsing_brittleness(self):
        # Current implementation assumes a very specific format
        body = (
            b'--boundary\r\n'
            b'Content-Disposition: form-data; name="username"\r\n\r\n'
            b'raymond\r\n'
            b'--boundary\r\n'
            b'Content-Disposition: form-data; name="email"\r\n\r\n'
            b'raymond@example.com\r\n'
            b'--boundary--\r\n'
        )
        
        headers = [
            (b'content-type', b'multipart/form-data; boundary=boundary'),
            (b'content-length', str(len(body)).encode())
        ]
        
        scope = {
            'type': 'http',
            'method': 'POST',
            'headers': headers,
        }
        
        def mock_receive():
            return {'type': 'http.request', 'body': body, 'more_body': False}
            
        from heaven.utils import preprocessor
        metadata = preprocessor(scope)
        request = Request(scope, body, mock_receive, metadata)
        
        # Test if it can retrieve data
        form = request.form
        self.assertIsNotNone(form)
        self.assertEqual(form.username, 'raymond')
        self.assertEqual(form.email, 'raymond@example.com')

    def test_url_encoded_form_parsing_missing(self):
        body = b'username=raymond&email=raymond%40example.com'
        headers = [
            (b'content-type', b'application/x-www-form-urlencoded'),
            (b'content-length', str(len(body)).encode())
        ]
        scope = {
            'type': 'http',
            'method': 'POST',
            'headers': headers,
        }
        from heaven.utils import preprocessor
        metadata = preprocessor(scope)
        request = Request(scope, body, None, metadata)
        
        # Now it should NOT be None
        form = request.form
        self.assertIsNotNone(form)
        self.assertEqual(form.username, 'raymond')
        self.assertEqual(form.email, 'raymond@example.com')

    def test_multi_value_parsing(self):
        body = b'interests=coding&interests=gaming&name=ray'
        headers = [
            (b'content-type', b'application/x-www-form-urlencoded'),
            (b'content-length', str(len(body)).encode())
        ]
        scope = {
            'type': 'http',
            'method': 'POST',
            'headers': headers,
        }
        from heaven.utils import preprocessor
        metadata = preprocessor(scope)
        request = Request(scope, body, None, metadata)
        
        form = request.form
        self.assertEqual(form.interests, ['coding', 'gaming'])
        self.assertEqual(form.name, 'ray')

if __name__ == '__main__':
    unittest.main()
