# Min 09-10 — The Request 📨

`req` is everything the client sent, already parsed. It is the **read** half of a handler.

```python
async def handler(req, res, ctx):
    ...
```

## Where the data lives

| You want | Read it from | Type |
| :--- | :--- | :--- |
| `/users/42` → `42` | `req.params.get('id')` | str, or the declared type |
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

Add a type to get it converted instead of a string:

```python
app.GET('/users/:id:int', handler)      # req.params.get('id')  -> 42
app.GET('/report/:day:date', handler)   # req.params.get('day') -> date(2026, 8, 1)
app.GET('/item/:sku:uuid', handler)     # req.params.get('sku') -> UUID(...)
```

Path segments and query strings accept the same seven names: `:int`, `:float`, `:bool`, `:str`, `:date`, `:datetime`, `:uuid`. See [the router](router.md#path-parameters) for the full table.

!!! note "Paths and query strings differ on bad input"
    A path segment that cannot convert makes the route **not match**, so the request falls through to another route or 404 and your handler never sees an unconverted value. A query string is more forgiving and hands you the raw string instead, because a bad `?page=` should not hide the whole endpoint.

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

Supported: `:int`, `:float`, `:bool`, `:str`, `:date`, `:datetime`, `:uuid`. The same names work in [path segments](#path-parameters).

!!! note "Bad input does not raise"
    `?page=banana` gives you the string `'banana'`, not a 422. A `:bool` that cannot be read is the one exception and comes back `False`. Check anything you rely on.

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

A `File` also carries `.content_type`, `.size`, `.save(path)` to copy it somewhere in chunks, and `.file`, a file object for handing to anything that reads files.

!!! warning "On a buffered route, `req.form` holds the whole upload in memory"
    Parsing a buffered form keeps the request body and the parsed parts side by side, so peak memory is a multiple of the upload size. That is fine for an avatar and wrong for a video.

    Two things to reach for, covered in [Serving Files](files.md#receiving-uploads):

    - **`App(max_body_size=...)`** caps what any buffered route will accept, answering `413` and stopping the read rather than accumulating the rest.
    - **`stream=True`** on the route leaves the body unread. Consume it raw with `req.stream()`, or parse it incrementally with `await req.form`.

On a route registered with `stream=True`, the form must be awaited, and large file parts spill to a temporary file on disk instead of accumulating in memory:

```python
app.POST('/upload', upload, stream=True)

async def upload(req, res, ctx):
    form = await req.form               # parses the body as it arrives

    form.get('title')                   # fields work as usual
    form.get('video').save(destination) # the file never sat in memory
```

Awaiting `req.form` on a buffered route is harmless, so the same handler body works on both kinds of route. Reading fields on a streaming route without awaiting first raises `RuntimeError`. The details (spill threshold, per-field ceilings, error draining) are in [Serving Files](files.md#parse-a-form-without-buffering-it).

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
