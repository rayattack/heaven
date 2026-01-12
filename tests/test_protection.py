import unittest
import msgspec
from heaven import App, Request, Response, Context
from heaven.router import Routes
from typing import List

class User(msgspec.Struct):
    id: int
    name: str

from heaven.constants import DEFAULT

class TestProtection(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.app = App(protect_output=True, fail_on_output=True)
        self.routes = self.app.subdomains[DEFAULT]

    async def mock_handle(self, method, path, handler_logic, schema_meta=None):
        # Helper to simulate a request through the router
        scope = {
            'type': 'http',
            'method': method,
            'path': path,
            'client': ('127.0.0.1', 8080),
            'query_string': b''
        }
        
        async def mock_receive():
            return {'type': 'http.request', 'body': b'', 'more_body': False}
        
        # Register handler
        self.app.abettor(method, path, handler_logic)
        if schema_meta:
            self.app.schema.add(method, path, **schema_meta)
        
        # Trigger baking
        self.app._bake_schemas()
        
        # Handle request
        return await self.routes.handle(scope, mock_receive, None, metadata=(DEFAULT, {}), application=self.app)

    async def test_protection_success(self):
        async def handler(req, res, ctx):
            res.body = {"id": 1, "name": "ray", "extra": "data"}
        
        res = await self.mock_handle('POST', '/user', handler, {'returns': User})
        
        # Data should be protected (extra dropped) and encoded to JSON
        import json
        data = json.loads(res.body)
        self.assertEqual(data, {"id": 1, "name": "ray"})
        self.assertNotIn("extra", data)
        self.assertEqual(res.status, 200)

    async def test_protection_missing_fields_strict(self):
        async def handler(req, res, ctx):
            res.body = {"id": 1} # 'name' missing
        
        res = await self.mock_handle('POST', '/user_strict', handler, {'returns': User, 'strict': True})
        
        # Should fail with 500 in strict mode
        self.assertEqual(res.status, 500)
        self.assertIn(b"Output Validation Error", res.body)

    async def test_protection_missing_fields_partial(self):
        async def handler(req, res, ctx):
            res.body = {"id": 1} # 'name' missing
        
        res = await self.mock_handle('POST', '/user_partial', handler, {'returns': User, 'partial': True, 'protect': True})
        
        # Should NOT fail if partial is True, it should just return the original data encoded
        import json
        data = json.loads(res.body)
        self.assertEqual(data, {"id": 1})
        self.assertEqual(res.status, 200)

    async def test_protection_off(self):
        async def handler(req, res, ctx):
            res.body = {"id": 1, "name": "ray", "extra": "data"}
        
        res = await self.mock_handle('POST', '/user_no_protect', handler, {'returns': User, 'protect': False})
        
        # Should NOT drop extra fields, but still encode to JSON if schema is present
        import json
        data = json.loads(res.body)
        self.assertEqual(data, {"id": 1, "name": "ray", "extra": "data"})
        self.assertEqual(res.status, 200)

    async def test_list_protection(self):
        async def handler(req, res, ctx):
            res.body = [
                {"id": 1, "name": "ray", "extra": "data"},
                {"id": 2, "name": "jane", "extra": "data"}
            ]
        
        res = await self.mock_handle('GET', '/users', handler, {'returns': List[User]})
        
        import json
        data = json.loads(res.body)
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0], {"id": 1, "name": "ray"})
        self.assertNotIn("extra", data[0])

if __name__ == '__main__':
    unittest.main()
