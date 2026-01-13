import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
import sys
from typing import List

# 1. Mock External Dependencies BEFORE imports
sys.modules['asyncpg'] = MagicMock()
sys.modules['msgspec'] = MagicMock()

from heaven import Router, Context, Request, Response
from plugins.heaven_pg import HeavenPG

# Define a Dummy Struct for testing binding
class User:
    id: int
    name: str

async def test_heaven_pg_fluent():
    print("Testing HeavenPG Fluent API...")
    
    app = Router()
    pg = HeavenPG("postgres://mock", name="db")
    app.plugin(pg)
    
    # Mock startup sequence (abbreviated)
    mock_pool = AsyncMock()
    sys.modules['asyncpg'].create_pool = AsyncMock(return_value=mock_pool)
    await pg.startup(app) # Direct call for simplicity
    
    ctx = Context(app)
    setattr(ctx, 'db', pg) # Direct injection for simplicity

    # 1. Test chaining .bind()
    print("1. Testing .bind(User)...")
    mock_pool.fetch.return_value = [{"id": 1, "name": "tersoo"}]
    
    def fake_convert_list(obj, type_):
        return [User()]
    sys.modules['msgspec'].convert = MagicMock(side_effect=fake_convert_list)
    
    # The Fluent Call
    result = await ctx.db.fetch("SELECT * FROM users").bind(User)
    
    mock_pool.fetch.assert_called_with("SELECT * FROM users", timeout=None)
    sys.modules['msgspec'].convert.assert_called()
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
    sys.modules['msgspec'].convert = MagicMock(side_effect=fake_convert_row)
    
    res_row = await ctx.db.fetchrow("SELECT 1").bind(User)
    mock_pool.fetchrow.assert_called()
    print("fetchrow bind executed successfully")
    
    await pg.shutdown(app)

if __name__ == "__main__":
    asyncio.run(test_heaven_pg_fluent())
