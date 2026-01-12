# Minute 8: The Earth 🌍

Testing web apps usually involves spinning up a "test client", fiddling with ports, or mocking complex internal states. Heaven gives you `Earth`, a testing utility that lets you verify your world without leaving Python.

## The Testing Philosophy

Heaven tests are:

1.  **In-Process**: No network overhead.

2.  **Explicit**: You see exactly what `req`, `res`, and `ctx` look like.

3.  **Flexible**: Test full lifecycles or atomic functions.

## 1. Full Integration Tests

Use the `test()` context manager to simulate a real server environment (including startup/shutdown hooks).

```python
# test_app.py
from main import app

async def test_create_user():
    async with app.earth.test() as earth:
        # 1. Send Request
        req, res, ctx = await earth.POST('/users', body={'name': 'Ray'})
        
        # 2. Assert Response
        assert res.status == 201
        assert res.json['name'] == 'Ray'
```

## 2. Unit Testing Handlers

Sometimes you just want to test a single function without running the whole router logic.

```python
from main import create_user_handler

async def test_handler_logic():
    # 1. Create fake components
    req = app.earth.req(url='/', body={'name': 'Ray'})
    res = app.earth.res()
    ctx = app.earth.ctx()

    # 2. Call handler directly
    await create_user_handler(req, res, ctx)

    # 3. Verify
    assert res.status == 201
```

## 3. Mocking & Swapping

You often need to mock databases or external services.

### Bucket Mocking
If your app uses `app.peek('db')`, you can overwrite it for the test.

```python
async with app.earth.test() as earth:
    # Overwrite the database connection
    app.keep('db', MockDatabase())
    
    await earth.GET('/users')
```

### Hook Swapping
Swap out a startup hook (like `connect_db`) with a mock version.

```python
# The real startup hook
async def connect_prod_db(app): ...

# The test startup hook
async def connect_test_db(app): ...

# Swap them
app.earth.swap(connect_prod_db, connect_test_db)
```

## 4. Subdomains & WebSockets

Earth handles everything Heaven handles.

```python
# Test a subdomain
await earth.GET('/admin', subdomain='admin')

# Test a WebSocket
ws = await earth.SOCKET('/chat').connect()
await ws.send('hello')
assert await ws.receive() == 'world'
await ws.close()
```

---

**Next:** It works locally. Let's show the world. On to **[Minute 9: Deployment](deployment.md)**.
