# Min 15-16 — The Context 🧠

`ctx` is request-scoped scratch space. It exists so hooks and handlers can pass data to each other without growing function signatures.

```python
async def handler(req, res, ctx):
    ...
```

## The division of labour

Heaven keeps the three objects strictly separate, and the split is the whole design:

| Object | Holds | Who writes it |
| :--- | :--- | :--- |
| `req` | what the client sent | the client |
| `ctx` | what the server worked out | your hooks and handlers |
| `res` | what you're sending back | you |

Other frameworks bolt server-computed state onto the request object. Heaven doesn't, so `req` stays a faithful record of what actually arrived over the wire.

## Passing data from a hook to a handler

This is what `ctx` is for, and it's the pattern behind almost all Heaven middleware:

```python
async def authenticate(req, res, ctx):
    user = await db.get_user(req.headers.get('authorization'))
    if not user:
        res.status = 401
        res.abort('Unauthorized')
    ctx.user = user                       # hand it forward

async def dashboard(req, res, ctx):
    res.body = {'welcome': ctx.user.name}  # already there

app.BEFORE('/dashboard', authenticate)
app.GET('/dashboard', dashboard)
```

## `keep`, `peek`, `unkeep`

Attribute access is the shorthand; the explicit methods do the same thing:

```python
ctx.keep('user', user)        # same as ctx.user = user
user = ctx.peek('user')       # same as ctx.user
user = ctx.unkeep('user')     # read and remove
```

!!! warning "Missing keys return `None`, they don't raise"
    `ctx.usr` (typo) quietly evaluates to `None` rather than raising `AttributeError`. A misspelled key looks exactly like a hook that didn't run. When a value is required, assert it:

    ```python
    user = ctx.peek('user')
    if user is None:
        raise RuntimeError('authenticate hook did not run')
    ```

### Typed keys

For larger apps, a `Key` gives you a checkable name instead of a bare string:

```python
from heaven import Key

CurrentUser = Key[User]('user')
IsAdmin = Key[bool]('is_admin')

async def authenticate(req, res, ctx):
    ctx.keep(CurrentUser, user)      # a type checker rejects the wrong type here

async def dashboard(req, res, ctx):
    user = ctx.peek(CurrentUser)     # inferred as User | None
```

The same keys work with `app.keep` / `app.peek` for application state.

## Request scope vs application scope

The distinction matters, and mixing them up causes data to leak between users:

```python
app.keep('db', pool)     # 🌍 lives for the whole process — pools, config, clients
ctx.keep('user', user)   # 📨 lives for one request — the caller, a request id
```

!!! danger "Never put per-request data on the app"
    `app.keep('current_user', user)` is shared by every concurrent request in the process. The next request will read someone else's user. Per-request data belongs on `ctx`, always.

## Reserved names

`session`, `app`, `request`, `response`, `headers` and `cookies` are reserved on the context and raise if you assign to them:

```python
ctx.my_data = 123        # fine
ctx.session = 'hacked'   # AttributeError
```

## Sessions

With `app.sessions()` enabled, the session lives on the context:

```python
ctx.session.user_id = 123      # write
uid = ctx.session.user_id      # read
```

Sessions are signed cookies — see [Min 27-28 — Security & Sessions](security.md).

---

**Next:** Intercepting the pipeline → **[Min 17-18 — Hooks](hooks.md)**
