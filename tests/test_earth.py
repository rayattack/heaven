import unittest
from heaven import App, Request, Response, Context
from heaven.constants import STARTUP, SHUTDOWN

class TestEarth(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.app = App()

    def test_atomic_factories(self):
        # Test long and short form factories
        req = self.app.earth.request('/foo')
        self.assertIsInstance(req, Request)
        self.assertEqual(req.url, '/foo')

        r = self.app.earth.req('/bar')
        self.assertEqual(r.url, '/bar')

        res = self.app.earth.response()
        self.assertIsInstance(res, Response)

        ctx = self.app.earth.context()
        self.assertIsInstance(ctx, Context)

        req, res, ctx = self.app.earth.trio()
        self.assertIsInstance(req, Request)
        self.assertIsInstance(res, Response)
        self.assertIsInstance(ctx, Context)

    async def test_integration_methods(self):
        # 1. Register a route
        async def handler(req, res, ctx):
            ctx.keep('hit', True)
            res.body = {"message": "hello", "method": req.method}
        
        self.app.POST('/hello', handler)

        # 2. Call via earth
        req, res, ctx = await self.app.earth.POST('/hello', body={"name": "ray"})

        # 3. Assertions
        self.assertEqual(res.status, 200)
        self.assertEqual(res.json, {"message": "hello", "method": "POST"})
        self.assertTrue(ctx.peek('hit'))

    async def test_lifecycle_and_sessions(self):
        started = False
        stopped = False

        async def startup(app):
            nonlocal started
            started = True

        async def shutdown(app):
            nonlocal stopped
            stopped = True

        self.app.ON(STARTUP, startup)
        self.app.ON(SHUTDOWN, shutdown)

        # Route that sets a cookie
        async def set_cookie(req, res, ctx):
            res.cookie('session', 'secret-val')
            res.body = "cookie set"

        # Route that checks a cookie
        async def check_cookie(req, res, ctx):
            cookie = req.cookies.get('session')
            res.body = f"cookie: {cookie}"

        self.app.GET('/set', set_cookie)
        self.app.GET('/check', check_cookie)

        # Use test context manager
        async with self.app.earth.test() as earth:
            self.assertTrue(started)
            
            # First request: Set cookie
            await earth.GET('/set')
            
            # Second request: Should have cookie automatically tracked
            req, res, ctx = await earth.GET('/check')
            self.assertEqual(res.text, "cookie: secret-val")

        self.assertTrue(stopped)

    async def test_query_string_simulation(self):
        async def handler(req, res, ctx):
            res.body = req.queries
        
        self.app.GET('/search', handler)

        req, res, ctx = await self.app.earth.GET('/search?q=heaven&p=1')
        self.assertEqual(res.json['q'], 'heaven')
        self.assertEqual(res.json['p'], '1')

    async def test_hook_swapping(self):
        real_run = False
        mock_run = False

        async def real_startup(app):
            nonlocal real_run
            real_run = True

        async def mock_startup(app):
            nonlocal mock_run
            mock_run = True

        self.app.ON(STARTUP, real_startup)
        
        # Register the swap
        self.app.earth.swap(real_startup, mock_startup)

        async with self.app.earth.test() as earth:
            # mock_startup should have run, real_startup should NOT
            self.assertTrue(mock_run)
            self.assertFalse(real_run)

    async def test_bucket_overwriting(self):
        async def real_startup(app):
            app.keep('db', 'REAL_DB')

        self.app.ON(STARTUP, real_startup)

        async with self.app.earth.test() as earth:
            # Immediately overwrite after startup hooks ran
            self.app.keep('db', 'MOCK_DB')
            
            async def handler(req, res, ctx):
                res.body = {"db": self.app.peek('db')}
            
            self.app.GET('/db', handler)
            req, res, ctx = await earth.GET('/db')
            self.assertEqual(res.json['db'], 'MOCK_DB')

    async def test_subdomain_support(self):
        # Register on 'api' subdomain
        self.app.subdomain('api')
        async def api_handler(req, res, ctx):
            res.body = {"subdomain": req.subdomain}
        
        self.app.GET('/info', api_handler, subdomain='api')

        # Test hitting 'api' subdomain
        req, res, ctx = await self.app.earth.GET('/info', subdomain='api')
        self.assertEqual(res.status, 200)
        self.assertEqual(res.json['subdomain'], 'api')

    async def test_middleware_bypass(self):
        middleware_run = False
        async def heavy_middleware(req, res, ctx):
            nonlocal middleware_run
            middleware_run = True

        self.app.BEFORE('/protected', heavy_middleware)
        
        async def handler(req, res, ctx):
            res.body = "ok"
        
        self.app.GET('/protected', handler)

        # Register bypass
        self.app.earth.bypass(heavy_middleware)

        async with self.app.earth.test() as earth:
            await earth.GET('/protected')
            self.assertFalse(middleware_run)

    async def test_upload_helper(self):
        async def handler(req, res, ctx):
            # req.form should be populated
            res.body = {
                "field": req.form.get('id'),
                "file_name": req.form.get('avatar').filename,
                "file_content": req.form.get('avatar').content.decode()
            }
        
        self.app.POST('/upload', handler)

        files = {'avatar': ( 'pic.png', b'binary_content' )}
        req, res, ctx = await self.app.earth.upload('/upload', files=files, data={'id': '123'})
        
        self.assertEqual(res.status, 200)
        self.assertEqual(res.json['field'], '123')
        self.assertEqual(res.json['file_name'], 'pic.png')
        self.assertEqual(res.json['file_content'], 'binary_content')

    async def test_websocket_simulation(self):
        # Register a websocket route
        async def chat_handler(req, res, ctx):
            # Manual websocket handling in heaven for now
            # Typically using SOCKET method but let's assume a handler exists
            pass
        
        # Heaven's SOCKET method for registering
        async def my_socket_handler(sender, receiver, req, ctx):
            msg = await receiver()
            await sender(f"Hello {msg}")
        
        self.app.SOCKET('/chat', my_socket_handler)

        ws = await self.app.earth.SOCKET('/chat').connect()
        self.assertTrue(ws.accepted)

        await ws.send("Ray")
        resp = await ws.receive()
        self.assertEqual(resp, "Hello Ray")

        await ws.close()
        self.assertTrue(ws.closed)

if __name__ == '__main__':
    unittest.main()
