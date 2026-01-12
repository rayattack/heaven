import os
import json
import msgspec
from unittest import IsolatedAsyncioTestCase
from heaven import App, Request, Response, Context
from heaven.mocks import _get_mock_receiver
from http import HTTPStatus

class User(msgspec.Struct):
    id: int
    name: str

class SchemaTest(IsolatedAsyncioTestCase):
    def setUp(self):
        self.app = App()

    async def test_schema_validation_success(self):
        async def handler(req, res, ctx):
            res.body = json.dumps({"received": req.data.name}).encode()

        self.app.POST("/users", handler)
        self.app.schema.POST("/users", expects=User)
        
        scope = {
            'type': 'http',
            'method': 'POST',
            'path': '/users',
            'headers': [[b'content-type', b'application/json']]
        }
        
        body = json.dumps({"id": 1, "name": "Raymond"}).encode()
        
        async def receive():
            return {'type': 'http.request', 'body': body, 'more_body': False}
        
        results = []
        async def send(message):
            results.append(message)
            
        await self.app(scope, receive, send)
        
        # Check for success
        start_msg = next(r for r in results if r['type'] == 'http.response.start')
        self.assertEqual(start_msg['status'], 200)
        
        body_msg = next(r for r in results if r['type'] == 'http.response.body')
        self.assertEqual(json.loads(body_msg['body']), {"received": "Raymond"})

    async def test_schema_validation_failure(self):
        async def handler(req, res, ctx):
            res.body = b"should not be reached"

        self.app.POST("/users", handler)
        self.app.schema.POST("/users", expects=User)
        
        scope = {
            'type': 'http',
            'method': 'POST',
            'path': '/users',
            'headers': [[b'content-type', b'application/json']]
        }
        
        # Missing 'id'
        body = json.dumps({"name": "Raymond"}).encode()
        
        async def receive():
            return {'type': 'http.request', 'body': body, 'more_body': False}
        
        results = []
        async def send(message):
            results.append(message)
            
        await self.app(scope, receive, send)
        
        # Check for 422
        start_msg = next(r for r in results if r['type'] == 'http.response.start')
        self.assertEqual(start_msg['status'], 422)

    async def test_openapi_generation(self):
        self.app.schema.POST("/users", expects=User, returns=User, summary="Create User")
        
        openapi = self.app.openapi()
        self.assertEqual(openapi["openapi"], "3.1.0")
        self.assertIn("/users", openapi["paths"])
        self.assertIn("post", openapi["paths"]["/users"])
        self.assertEqual(openapi["paths"]["/users"]["post"]["summary"], "Create User")
        self.assertIn("User", openapi["components"]["schemas"])

    async def test_docs_endpoint(self):
        self.app.DOCS("/api/docs")
        
        # Check openapi.json
        scope = {
            'type': 'http',
            'method': 'GET',
            'path': '/api/docs/openapi.json',
            'headers': []
        }
        
        results = []
        async def send(message):
            results.append(message)
            
        async def receive():
            return {'type': 'http.request'}

        await self.app(scope, receive, send)
        
        start_msg = next(r for r in results if r['type'] == 'http.response.start')
        self.assertEqual(start_msg['status'], 200)
        
        # Check HTML
        scope['path'] = '/api/docs'
        results = []
        await self.app(scope, receive, send)
        
        start_msg = next(r for r in results if r['type'] == 'http.response.start')
        self.assertEqual(start_msg['status'], 200)
        
        body_msg = next(r for r in results if r['type'] == 'http.response.body')
        self.assertIn(b"<title>API Reference</title>", body_msg['body'])
        self.assertIn(b"scalar/api-reference", body_msg['body'])
