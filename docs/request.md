# Min 09-10 — The Request 📨

`req` is everything the client sent, already parsed. It is the **read** half of a handler.

```python
async def handler(req, res, ctx):
    ...
```

## Where the data lives

| You want | Read it from | Type |
| :--- | :--- | :--- |
| `/users/42` → `42` | `req.params.get('id')` | str, or int with `:int` |
| `?page=3` | `req.queries.get('page')` | str, or coerced |
| A JSON body | `req.json` | dict / list |
| A **validated** body | `req.data` | dict (see [Schemas](schema.md)) |
| A form or upload | `req.form.get('field')` | str or `File` |
| Raw bytes | `req.body` | bytes |
| Headers | `req.headers.get('authorization')` | str |
| Cookies | `req.cookies.get('session')` | str |

## Path parameters

```python
app.GET('/users/:id/orders/:order_id', handler)

async def handler(req, res, ctx):
    req.params.get('id')        # '42'
    req.params.get('order_id')  # '7'
```

Add `:int` to get an integer instead of a string:

```python
app.GET('/users/:id:int', handler)   # req.params.get('id') -> 42
```

!!! warning "`:int` is the only path cast that works"
    `/report/:day:date` and `/item/:sku:uuid` are accepted without complaint but still hand you a **string**. Only `:int` (and the no-op `:str`) actually convert. Query strings are different — they support the full type set.

## Query strings

Read them straight off `req.queries`:

```python
# GET /search?q=heaven&page=3
req.queries.get('q')      # 'heaven'
req.queries.get('page')   # '3'  -> a string, by default
```

Declare types in the route to have them coerced:

```python
app.GET('/search?page:int&since:date&exact:bool', search)

req.queries.get('page')    # 3                 int
req.queries.get('since')   # date(2026, 1, 1)  date
req.queries.get('exact')   # True              bool
```

Supported: `:int`, `:float`, `:bool`, `:str`, `:date`, `:datetime`, `:uuid`.

!!! note "Bad input does not raise"
    `?page=banana` gives you the string `'banana'`, not a 422. Check anything you rely on.

## JSON bodies

`req.json` decodes the raw body with `orjson` every time you touch it:

```python
async def create(req, res, ctx):
    payload = req.json          # {'name': 'Ada'}
```

`req.data` is the better habit. With a schema registered it holds the **validated** body; without one it falls back to `req.json`.

```python
app.schema.POST('/users', expects=User)

async def create(req, res, ctx):
    user = req.data             # guaranteed to satisfy User
    res.body = {'name': user['name']}
```

### Type-safe `req.data`

`Request` is generic — annotate it and your editor autocompletes the payload:

```python
from heaven import Request, Response, Context

async def create_user(req: Request[User], res: Response, ctx: Context):
    user = req.data      # your IDE knows the shape
```

This is a convention for your type checker; the runtime doesn't verify the annotation matches what you registered.

## Forms and uploads

`req.form` parses `application/x-www-form-urlencoded` and `multipart/form-data`.

```python
async def upload(req, res, ctx):
    form = req.form

    username = form.get('username')     # str
    avatar   = form.get('avatar')       # a File object

    avatar.filename                     # 'photo.png'
    avatar.content                      # bytes
```

`req.form` is `None` when the request has no form content type — check before using it.

!!! danger "Uploads are held entirely in memory"
    Heaven buffers the whole request body before your handler runs, and there is **no size limit**. A large upload is a memory spike, and a hostile one is a denial of service. Put a body-size cap in your reverse proxy (`client_max_body_size` in Nginx) before accepting uploads from the public.

## Metadata

```python
req.method        # 'POST'
req.url           # '/users/1?active=true'
req.route         # '/users/:id'      — the pattern that matched
req.subdomain     # 'api'
req.host          # 'api.example.com'
req.scheme        # 'http'
req.ip.address    # '203.0.113.9'
req.ip.port       # 54123
req.app           # the Router — use req.app.peek('db')
```

!!! tip "`req.app` is how you reach shared resources"
    Anything you stored at startup with `app.keep()` is one hop away:

    ```python
    async def list_users(req, res, ctx):
        db = req.app.peek('db')
        res.body = await db.fetch('SELECT * FROM users')
    ```

---

**Next:** You've heard them. Now answer → **[Min 11-12 — The Response](response.md)**
