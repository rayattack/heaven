# Min 23-24 — Testing with Earth 🌍

Earth is Heaven's built-in test client. No ports, no sockets, no `httpx` — it drives your app in-process and hands you back the same three objects your handlers see.

```python
req, res, ctx = await app.earth.GET('/users')
```

That return shape is the point: you can assert on the **response** and also inspect the **context** your hooks built, which is normally invisible from outside.

## Integration tests

`app.earth.test()` is an async context manager that runs your startup hooks on entry and your shutdown hooks on exit.

```python
from unittest import IsolatedAsyncioTestCase
from main import app

class TestUsers(IsolatedAsyncioTestCase):
    async def test_create_user(self):
        async with app.earth.test() as earth:
            req, res, ctx = await earth.POST('/users', body={'name': 'Ada'})

            self.assertEqual(res.status, 201)
            self.assertEqual(res.json['name'], 'Ada')
```

A `dict` or `list` body is JSON-encoded and given the right content type automatically. Cookies and sessions are tracked across requests within a block, so a login followed by a protected request works as it would in a browser.

Available: `GET`, `POST`, `PUT`, `PATCH`, `DELETE`, plus `upload()` and `SOCKET()`.

!!! danger "Earth skips Heaven's final response step"
    Earth calls the router directly rather than going through the full ASGI entry point, so a few things that happen in production **do not happen in tests**:

    - a `dict`/`list` body is **not** serialized — `res.body` is still a `dict`, and `res.headers` has no `Content-Type`
    - `res.defer()` callbacks never run
    - the debug error page is never rendered

    In practice: assert against `res.json` (which handles both) rather than `res.body`, and test deferred work by calling the callback directly.

## Unit-testing a handler

Skip routing entirely and build the three objects yourself:

```python
from main import create_user

async def test_handler_logic():
    req = app.earth.req(url='/users', body={'name': 'Ada'})
    res = app.earth.res()
    ctx = app.earth.ctx()

    await create_user(req, res, ctx)

    assert res.status == 201
```

This is where the `(req, res, ctx)` signature pays off — a handler is a plain function, so calling it needs no framework machinery.

## Replacing dependencies

### Swap a lifecycle hook

Point startup at a test database instead of the real one:

```python
app.earth.swap(connect_prod_db, connect_test_db)
```

### Skip a hook

Rate limiters and auth guards usually get in the way of tests:

```python
app.earth.bypass(rate_limiter)
```

### Mock app state

```python
async with app.earth.test() as earth:
    original = app.unkeep('db')
    app.keep('db', MockDatabase())
    try:
        req, res, ctx = await earth.GET('/users')
    finally:
        app.keep('db', original)      # always restore
```

!!! warning "`app.keep` outlives the test"
    Application state is not reset between tests. Overwrite it without restoring and every later test in the process gets your mock. The `try/finally` above is not optional.

## Subdomains, sockets and uploads

```python
# a subdomain, with no DNS involved
req, res, ctx = await earth.GET('/users', subdomain='api')

# a websocket
ws = await earth.SOCKET('/chat').connect()
await ws.send('hello')
assert await ws.receive() == 'world'
await ws.close()

# a multipart upload
req, res, ctx = await earth.upload('/avatar',
    files={'file': ('image.png', b'\x89PNG...')},
    data={'userid': '123'},
)
```

## Running the suite

Heaven's own tests use `unittest.IsolatedAsyncioTestCase` and run under pytest:

<div class="termy">

```console
$ python -m pytest tests/ -v
```

</div>

---

**Next:** Work that happens outside a request → **[Min 25-26 — Background Work](daemons.md)**
