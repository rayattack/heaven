import os
import json
from typing import TypedDict
from unittest import IsolatedAsyncioTestCase

from heaven import App, Request, Response, Context
from heaven.mocks import _get_mock_receiver
from http import HTTPStatus
from orjson import dumps, loads

class User(TypedDict):
    id: int
    name: str

class SchemaTest(IsolatedAsyncioTestCase):
    def setUp(self):
        self.app = App()

    async def test_schema_validation_success(self):
        async def handler(req, res, ctx):
            res.body = dumps({"received": req.data['name']})

        self.app.POST("/users", handler)
        self.app.schema.POST("/users", expects=User)
        
        scope = {
            'type': 'http',
            'method': 'POST',
            'path': '/users',
            'client': ('127.0.0.1', 8000),
            'headers': [[b'content-type', b'application/json']]
        }
        
        body = dumps({"id": 1, "name": "Raymond"})
        
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
        self.assertEqual(loads(body_msg['body']), {"received": "Raymond"})

    async def test_schema_validation_failure(self):
        async def handler(req, res, ctx):
            res.body = b"should not be reached"

        self.app.POST("/users", handler)
        self.app.schema.POST("/users", expects=User)
        
        scope = {
            'type': 'http',
            'method': 'POST',
            'path': '/users',
            'client': ('127.0.0.1', 8000),
            'headers': [[b'content-type', b'application/json']]
        }
        
        # Missing 'id'
        body = dumps({"name": "Raymond"})
        
        async def receive():
            return {'type': 'http.request', 'body': body, 'more_body': False}
        
        results = []
        async def send(message):
            results.append(message)
            
        await self.app(scope, receive, send)
        
        # Check for 422
        start_msg = next(r for r in results if r['type'] == 'http.response.start')
        self.assertEqual(start_msg['status'], 422)

    async def test_schema_dot_access(self):
        captured = {}
        async def handler(req, res, ctx):
            captured['data'] = req.data
            captured['name'] = req.data.name
            res.body = dumps({"received": req.data.name})

        self.app.POST("/users", handler)
        self.app.schema.POST("/users", expects=User, dot=True)

        scope = {
            'type': 'http',
            'method': 'POST',
            'path': '/users',
            'client': ('127.0.0.1', 8000),
            'headers': [[b'content-type', b'application/json']]
        }
        body = dumps({"id": 1, "name": "Raymond"})

        async def receive():
            return {'type': 'http.request', 'body': body, 'more_body': False}
        results = []
        async def send(message):
            results.append(message)

        await self.app(scope, receive, send)

        start_msg = next(r for r in results if r['type'] == 'http.response.start')
        self.assertEqual(start_msg['status'], 200)
        self.assertEqual(captured['name'], "Raymond")
        self.assertEqual(captured['data']['id'], 1)

    async def test_schema_default_is_plain_dict(self):
        captured = {}
        async def handler(req, res, ctx):
            captured['data'] = req.data
            res.body = b"ok"

        self.app.POST("/users", handler)
        self.app.schema.POST("/users", expects=User)

        scope = {
            'type': 'http',
            'method': 'POST',
            'path': '/users',
            'client': ('127.0.0.1', 8000),
            'headers': [[b'content-type', b'application/json']]
        }
        body = dumps({"id": 1, "name": "Raymond"})

        async def receive():
            return {'type': 'http.request', 'body': body, 'more_body': False}
        results = []
        async def send(message):
            results.append(message)

        await self.app(scope, receive, send)

        with self.assertRaises(AttributeError):
            _ = captured['data'].name

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
            'client': ('127.0.0.1', 8000),
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
