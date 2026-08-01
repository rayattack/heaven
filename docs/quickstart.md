# Min 01-02 — The Beginning ⚡

The clock starts now. Two minutes to a running server.

## Install

<div class="termy">

```console
$ pip install heaven

---> 100%
Successfully installed heaven
```

</div>

## Write it

Create a file named `app.py`:

```python
from heaven import App

app = App()

# Every handler in Heaven takes exactly three arguments.
async def hello(req, res, ctx):
    res.body = 'Hello from Heaven'

# Map GET / to the hello handler.
app.GET('/', hello)
```

Two things to notice, because they hold for the entire framework:

1. **Registration is a method call**, not a decorator. `app.GET(route, handler)`.
2. **The handler signature never changes.** `(req, res, ctx)` — for routes, hooks, and websockets alike.

!!! tip "Handlers can be sync too"
    `async def` is the right default, but a plain `def hello(req, res, ctx)` works identically. Heaven checks and calls it correctly. Use sync handlers freely for CPU-only work with no `await` in it.

## Fly it

<div class="termy">

```console
$ heaven fly

INFO:     Started server process [1234]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

</div>

Open `http://localhost:8000`. That's a running server, and you've spent two minutes.

## Returning JSON

Assign a `dict` or a `list` and Heaven serializes it with `orjson` and sets `Content-Type: application/json` for you.

```python
async def hello(req, res, ctx):
    res.body = {'message': 'Hello from Heaven'}   # -> {"message":"Hello from Heaven"}
```

!!! warning "`res.body =`, not `return`"
    Heaven ignores whatever your handler returns. You communicate by **writing to `res`**. This trips up everyone arriving from FastAPI exactly once, and then never again.

    ```python
    async def wrong(req, res, ctx):
        return {'message': 'this is discarded'}    # ❌ returns are ignored

    async def right(req, res, ctx):
        res.body = {'message': 'this is sent'}     # ✅
    ```

## Growing past one file

As soon as you have more than a handful of routes, stop importing handlers and pass their import path as a string instead.

```python
# handlers/users.py
async def get_profile(req, res, ctx):
    res.body = {'id': req.params.get('id')}
```

```python
# app.py
app.GET('/profile/:id:int', 'handlers.users.get_profile')
```

Heaven resolves the string at registration time. No import block, no circular imports, no decorator scanning.

---

**Next:** You're flying. Now take the controls → **[Min 03-04 — The Command Line](cli.md)**
