# Recipes

Patterns from real Heaven applications. Each one is self-contained — copy, adapt, move on.

## Authentication with a BEFORE hook

The idiomatic approach: verify in a hook, stash the user on `ctx`, let handlers assume it's there.

```python
import jwt

async def authenticate(req, res, ctx):
    header = req.headers.get('authorization', '')
    token = header.removeprefix('Bearer ').strip()

    try:
        claims = jwt.decode(token, req.app.CONFIG('SECRET_KEY'), algorithms=['HS256'])
    except jwt.PyJWTError:
        res.status = 401
        res.abort({'message': 'invalid or expired token'})
    else:
        ctx.current_user = claims['sub']

app.BEFORE('/api/*', authenticate)
```

!!! tip "Scope the guard to what it protects"
    Registering auth on the **exact prefix** it defends (`/api/*`) keeps it off routes that do not need it. A `/*` guard also works, since `BEFORE` hooks run from the broadest pattern inward. See [Hooks](hooks.md#execution-order).

## Role-based authorization

Layer a second hook after the first. Hooks run in registration order within the same pattern.

```python
def requires(*roles):
    async def guard(req, res, ctx):
        pool = req.app.peek('db')
        async with pool.acquire() as db:
            held = await db.fetchval(
                'SELECT roles FROM privileges WHERE user_id = $1', ctx.current_user)

        if not set(roles) & set(held or []):
            res.status = 403
            res.abort({'message': 'insufficient privileges'})
    return guard

app.BEFORE('/api/admin/*', authenticate)
app.BEFORE('/api/admin/*', requires('admin', 'owner'))
```

Building the hook from a factory keeps each registration a distinct function object — which also sidesteps the [method-scoping footgun](hooks.md#scoping-to-methods) around reusing one function in several places.

## A validated CRUD endpoint

```python
from typing import Annotated, Literal, NotRequired, TypedDict
from heaven import App, Request, Response, Context

app = App()

class CreateUser(TypedDict):
    email: Annotated[str, "format=email"]
    name:  Annotated[str, "min_len=1; max_len=120"]
    role:  NotRequired[Literal["guest", "member", "admin"]]

class UserOut(TypedDict):
    id: int
    email: str
    name: str
    role: str

async def create_user(req: Request[CreateUser], res: Response, ctx: Context):
    db = req.app.peek('db')
    row = await db.fetchrow(
        'INSERT INTO users (email, name, role) VALUES ($1, $2, $3) RETURNING *',
        req.data['email'], req.data['name'], req.data.get('role', 'guest'))

    res.status = 201
    res.body = dict(row)          # protect=True strips anything not in UserOut

app.schema.POST('/v1/users',
    expects=CreateUser,
    returns=UserOut,
    protect=True,
    summary='Create a user',
    group='Users',
)
app.POST('/v1/users', create_user)

app.DOCS('/docs', title='User Service')
```

You get a 422 on invalid input, `password_hash` can never leak through the response, and `/docs` documents it — from one registration.

## A connection pool for the whole app

```python
import asyncpg

async def open_pool(app):
    app.keep('db', await asyncpg.create_pool(dsn=os.environ['DATABASE_URL']))

async def close_pool(app):
    await app.peek('db').close()

app.ONCE(open_pool)
app.ON('shutdown', close_pool)
```

Reach it from any handler with `req.app.peek('db')`.

!!! danger "Startup failures don't stop the boot"
    If `open_pool` raises, Heaven logs it and starts anyway — leaving a server that 500s on every request. Exit explicitly if the pool is essential:

    ```python
    async def open_pool(app):
        try:
            app.keep('db', await asyncpg.create_pool(dsn=DSN))
        except Exception as exc:
            print(f'FATAL: database unreachable: {exc}')
            raise SystemExit(1)
    ```

## Paginated list endpoints

Typed query strings do the coercion for you:

```python
app.GET('/v1/orders?page:int&size:int&since:date', list_orders)

async def list_orders(req, res, ctx):
    page = req.queries.get('page') or 1
    size = min(req.queries.get('size') or 25, 100)      # always cap the page size

    db = req.app.peek('db')
    rows = await db.fetch(
        'SELECT * FROM orders WHERE created_at > $1 ORDER BY id LIMIT $2 OFFSET $3',
        req.queries.get('since'), size, (page - 1) * size)

    res.body = {'page': page, 'size': size, 'items': [dict(r) for r in rows]}
```

Remember that bad input coerces silently — `?page=banana` gives you the string, hence the `or 1` and the explicit cap.

## A JSON error envelope

Heaven's 422 is plain text. If your API promises JSON errors, normalize in an `AFTER` hook:

```python
import orjson

async def json_errors(req, res, ctx):
    if res.status >= 400 and not isinstance(res.body, (dict, list)):
        res.headers = 'Content-Type', 'application/json'
        res.body = orjson.dumps({
            'error': {'status': int(res.status), 'message': res.text},
        })

app.AFTER('/api/*', json_errors)
```

!!! warning "This won't catch validation failures"
    A 422 calls `res.abort()`, which skips every `AFTER` hook — so this hook never sees it. It normalizes errors your own handlers set. Shaping the validation 422 itself requires framework support that doesn't exist yet.

## Health checks

```python
async def health(req, res, ctx):
    try:
        await req.app.peek('db').fetchval('SELECT 1')
    except Exception:
        res.status = 503
        res.body = {'status': 'degraded'}
    else:
        res.body = {'status': 'ok'}

app.GET('/health', health)
```

Keep it out of your API docs group, or give it its own: `group='Monitoring'`.

## Serving a small SPA

```python
app.TEMPLATES('dist', relative_to=__file__)

async def index(req, res, ctx):
    await res.render('index.html')

app.GET('/', index)
app.GET('/app/*', index)      # let the client router handle deep links
```

Serve the compiled assets from your proxy rather than `app.ASSETS()` — see [Templates & Assets](html.md#static-files).
