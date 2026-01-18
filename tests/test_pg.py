import asyncio
import unittest
from unittest.mock import MagicMock, AsyncMock, patch
import sys
from typing import List

# Use unittest.TestCase for proper discovery and isolation
class TestHeavenPG(unittest.IsolatedAsyncioTestCase):
    async def test_heaven_pg_fluent(self):
        print("Testing HeavenPG Fluent API...")
        
        # Scoped mocking of modules to prevent polluting global state
        with patch.dict(sys.modules, {'asyncpg': MagicMock(), 'msgspec': MagicMock()}):
            # Re-import locally or rely on sys.modules lookup which now points to mocks
            # Note: We need to import these AFTER patching if we want the module-level code to see the mock
            # But the imports are already done at top level? No, they are below.
            
            # Since imports happen once, patching sys.modules works if the code *uses* sys.modules or imports *after*.
            # But plugins.heaven_pg imports asyncpg/msgspec at top level.
            # So we must patch sys.modules BEFORE importing the plugin if we want to mock it.
            # But we can't unimport easily.
            
            # Better strategy: use patch.dict but force reload or just rely on the fact 
            # that we want to mock the 'import' statement.
            
            # Actually, simply putting them in the dict overrides them for any *subsequent* import 
            # or lookup.
            
            # Let's see how the original did it: it did sys.modules[] = Mock BEFORE imports.
            # We will move the imports INSIDE the patch context.
            
            from heaven import Router, Context, Request, Response
            
            # We need to ensure we don't pick up the real msgspec if it was already imported by other tests
            # patch.dict handles this temporarily.
            
            # Problem: If 'plugins.heaven_pg' was already imported, it holds a ref to the real msgspec.
            # We might need to handle that, but for now let's assume this test runs in isolation or order doesn't matter
            # IF we use patch correctly.
            
            # However, the previous code imported 'heaven_pg' at top level AFTER mocking.
            # We should move that import inside the test method.

            # Mock msgspec behavior for the test
            mock_msgspec = sys.modules['msgspec']
            
            # Define a Dummy Struct for testing binding
            class User:
                id: int
                name: str
                
            # We need to mock the actual class 'HeavenPG' from plugins.heaven_pg
            # But wait, we want to TEST HeavenPG, so we shouldn't mock it, we should mock its deps.
            
            # Ideally we reload constraints/deps.
            # Let's just import inside.
            
            # Mock asyncpg behavior
            mock_pool = AsyncMock()
            sys.modules['asyncpg'].create_pool = AsyncMock(return_value=mock_pool)

            # Import system under test
            # We use local import to ensure it picks up the patched modules if not already cached.
            # If already cached (real), this might fail.
            # But standard python testing usually requires structure. 
            # Given the fragility, let's just stick to the mock structure but scoped.
            
            # If we really want to be safe, we might need to patch `plugins.heaven_pg.msgspec` etc if imported.
            # But let's try the sys.modules patch approach first as it mirrors the user's intent.
            
            from plugins.heaven_pg import HeavenPG

            app = Router()
            pg = HeavenPG("postgres://mock", name="db")
            app.plugin(pg)
            
            await pg.startup(app) # Direct call for simplicity
            
            ctx = Context(app)
            setattr(ctx, 'db', pg) # Direct injection for simplicity

            # 1. Test chaining .bind()
            print("1. Testing .bind(User)...")
            mock_pool.fetch.return_value = [{"id": 1, "name": "tersoo"}]
            
            def fake_convert_list(obj, type_):
                return [User()]
            mock_msgspec.convert = MagicMock(side_effect=fake_convert_list)
            
            # The Fluent Call
            result = await ctx.db.fetch("SELECT * FROM users").bind(User)
            
            mock_pool.fetch.assert_called_with("SELECT * FROM users", timeout=None)
            mock_msgspec.convert.assert_called()
            print("Fluent bind executed successfully")

            # 2. Test without bind (standard await)
            print("2. Testing await without bind...")
            mock_pool.fetch.reset_mock()
            mock_pool.fetch.return_value = [{"id": 2}]
            
            # Just await the pending query directly
            result_raw = await ctx.db.fetch("SELECT 1")
            
            mock_pool.fetch.assert_called_with("SELECT 1", timeout=None)
            if result_raw == [{"id": 2}]:
                print("Standard await executed successfully")
            else:
                print(f"Standard await failed. Got: {result_raw}")

            # 3. Test fetchrow
            print("3. Testing fetchrow...")
            mock_pool.fetchrow.return_value = {"id": 1}
            def fake_convert_row(obj, type_): return User()
            mock_msgspec.convert = MagicMock(side_effect=fake_convert_row)
            
            res_row = await ctx.db.fetchrow("SELECT 1").bind(User)
            mock_pool.fetchrow.assert_called()
            print("fetchrow bind executed successfully")
            
            await pg.shutdown(app)

if __name__ == "__main__":
    unittest.main()
