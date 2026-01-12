import os
import shutil
import tempfile
import mimetypes
from unittest import IsolatedAsyncioTestCase
from heaven import Response, Router, Context
from heaven.mocks import MockRequest, _get_mock_receiver
from http import HTTPStatus
from collections import deque

class FileServingTest(IsolatedAsyncioTestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.assets_dir = os.path.join(self.test_dir, "assets")
        os.mkdir(self.assets_dir)
        self.test_file_path = os.path.join(self.assets_dir, "test.txt")
        with open(self.test_file_path, "w") as f:
            f.write("hello world")
        
        self.router = Router()
        self.context = Context(self.router)
        self.request = MockRequest('/test')
        self.res = Response(app=self.router, context=self.context, request=self.request)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_response_file_not_found(self):
        self.res.file('/non/existent/path')
        self.assertEqual(self.res.status, HTTPStatus.NOT_FOUND)
        self.assertEqual(self.res.body, b'File not found')

    async def test_response_file_exists(self):
        self.res.file(self.test_file_path)
        self.assertEqual(self.res.status, HTTPStatus.OK)
        
        headers = {k.decode().lower(): v.decode() for k, v in self.res.headers}
        self.assertEqual(headers['content-type'], 'text/plain')
        self.assertIn('filename="test.txt"', headers['content-disposition'])
        self.assertTrue(hasattr(self.res.body, '__aiter__'))

    async def test_streaming_response(self):
        self.res.file(self.test_file_path)
        
        chunks = []
        async for chunk in self.res.body:
            chunks.append(chunk)
        
        self.assertEqual(b"".join(chunks), b"hello world")

    async def test_router_assets(self):
        # We use relative_to to point to the temp assets dir
        self.router.ASSETS(folder='assets', route='/static/*', relative_to=self.assets_dir)
        
        scope = {
            'type': 'http',
            'method': 'GET',
            'path': '/static/test.txt',
            'headers': [[b'host', b'localhost']]
        }
        
        async def receive():
            return {'type': 'http.request'}
        
        results = []
        async def send(message):
            results.append(message)
        
        await self.router(scope, receive, send)
        
        # Verify results
        self.assertTrue(any(r['type'] == 'http.response.start' and r['status'] == 200 for r in results))
        
        body = b"".join([r['body'] for r in results if r['type'] == 'http.response.body'])
        self.assertEqual(body, b"hello world")
        
        start_msg = next(r for r in results if r['type'] == 'http.response.start')
        headers = {k.decode().lower(): v.decode() for k, v in start_msg['headers']}
        self.assertEqual(headers['content-type'], 'text/plain')
