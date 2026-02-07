# The Earth 🌍

Testing web apps usually involves spinning up a "test client", fiddling with ports, or mocking complex internal states. Heaven gives you `Earth`, a testing utility that lets you verify your world without leaving Python.

## The Testing Philosophy

Heaven tests are:

1.  **In-Process**: No network overhead.
2.  **Explicit**: You see exactly what `req`, `res`, and `ctx` look like.
3.  **Flexible**: Test full lifecycles, atomic functions, or swapped configurations.

## 1. Full Integration Tests

Use the `test()` context manager to simulate a real server environment (including startup/shutdown hooks).

```python
# test_app.py
from main import app

async def test_create_user():
    # track_session=True automatically handles Cookies across requests
    async with app.earth.test(track_session=True) as earth:
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

## 3. Mocking, Swapping & Bypassing

You often need to mock databases, avoid rate limits, or swap authentication logic.

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

### Middleware Bypassing
Skip specific middleware (like Rate Limiters) that might interfere with tests.

```python
# Don't run this middleware during tests
app.earth.bypass(rate_limiter_hook)
```

### Bucket Mocking
If your app uses `app.peek('db')`, you can overwrite it for the test.

!!! warning "Warning"
    `app.keep` is persistent across tests! If you overwrite a global dependency, you must manually restore it, otherwise downstream tests will use your mock.

```python
async with app.earth.test() as earth:
    # 1. Backup original
    original_db = app.unkeep('db')
    
    # 2. Overwrite with mock
    app.keep('db', MockDatabase())
    
    try:
        await earth.GET('/users')
    finally:
        # 3. Restore original for other tests
        app.keep('db', original_db)
```

## 4. Subdomains, WebSockets & File Uploads

Earth handles detailed scenarios easily.

```python
# Test a subdomain
await earth.GET('/admin', subdomain='admin')

# Test a WebSocket
ws = await earth.SOCKET('/chat').connect()
await ws.send('hello')
assert await ws.receive() == 'world'
await ws.close()

# Test File Uploads
await earth.upload('/avatar', 
    files={'file': ('image.png', b'data')},
    data={'userid': '123'}
)
```

---

**Next:** Confident much? Let your app run in the background with **[Daemons](daemons.md)**.