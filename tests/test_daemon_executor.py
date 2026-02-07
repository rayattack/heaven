from heaven import App
import time
import asyncio
import unittest

class TestDaemonBlocking(unittest.IsolatedAsyncioTestCase):
    async def test_sync_daemon_is_non_blocking(self):
        app = App()
        daemon_ran = False
        
        def blocking_daemon(app):
            nonlocal daemon_ran
            # This would normally block the entire event loop for 1 second
            time.sleep(1)
            daemon_ran = True
            return False # Stop after one run
            
        app.daemons = blocking_daemon
        
        async def fast_handler(req, res, ctx):
            res.body = "fast"
            
        app.GET('/fast', fast_handler)
        
        # Start daemons manually since we aren't using listen()
        await app._Router__rundaemons()
        
        # Immediately try to hit the fast handler
        # If the daemon blocked, this would take > 1 second
        start = time.time()
        req, res, ctx = await app.earth.GET('/fast')
        end = time.time()
        
        self.assertEqual(res.body, b"fast")
        self.assertLess(end - start, 0.5) # Should be near instantaneous
        
        # Wait for daemon to finish to be sure it actually ran
        await asyncio.sleep(1.2)
        self.assertTrue(daemon_ran)

if __name__ == '__main__':
    unittest.main()
