# Min 11-12 — The Response 🗣️

`res` is what you're sending back. It is the **write** half of a handler.

!!! warning "You write to `res`. You never `return`."
    Heaven discards your handler's return value. This is the one habit to unlearn coming from FastAPI or Flask.

    ```python
    async def handler(req, res, ctx):
        return {'a': 1}        # ❌ silently ignored
        res.body = {'a': 1}    # ✅
    ```

## The basics

```python
res.status = 201
res.body = {'id': 1, 'name': 'Ada'}
```

`res.body` accepts several types and does the right thing with each:

| You assign | Heaven sends |
| :--- | :--- |
| `dict` or `list` | JSON via `orjson`, with `Content-Type: application/json` set for you |
| `str` | the text, UTF-8 encoded |
| `bytes` | exactly those bytes |
| `int` / `float` | its string form |
| an async generator | a streamed response |

### Status codes by name

`res.http` is the standard library's `HTTPStatus`, already imported:

```python
res.status = res.http.CREATED           # 201
res.status = res.http.NOT_FOUND         # 404

if res.status == res.http.UNAUTHORIZED:
    ...
```

## Headers

Assign a `(key, value)` tuple. Assigning a header the response already carries **replaces** it, matched case-insensitively, so the last write wins and each name goes out exactly once:

```python
res.headers = 'X-Powered-By', 'Heaven'
res.headers = 'Cache-Control', 'no-store'
res.headers = 'cache-control', 'no-cache'    # replaces the line above
```

`res.header(key, value)` does the same thing and is chainable.

The assignment understands three more shapes:

```python
res.headers = 'X-Powered-By', None           # removes the header
res.headers = 'Vary', ['Origin', 'Accept']   # Vary: Origin, Accept
res.cookie('session', token)                 # Set-Cookie accumulates, one line each
```

!!! note "Why replace instead of append"
    HTTP allows a name to repeat on the wire only when its value is defined as a comma-separated list, which the list form above produces on a single line, and for `Set-Cookie`, which is why that one header accumulates. Sending a singleton like `Content-Type` twice is protocol-invalid and clients resolve the conflict unpredictably. Replacing also means built-ins that set their own headers, like `res.file()` setting `Content-Type`, override yours instead of sending both.

## Cookies

```python
res.cookie('session', token,
    max_age=3600,
    httponly=True,
    secure=True,
    samesite='Lax',
    path='/',
)
```

Also supported: `expires` (a `datetime`), `domain`, `partitioned`.

## Redirects

```python
res.redirect('/login')                      # 307 Temporary Redirect
res.redirect('/new-home', permanent=True)   # 308 Permanent Redirect
```

!!! note "307 and 308 only"
    Both preserve the original method and body, so a redirected `POST` stays a `POST`. If you need the classic "`POST` then `GET` the new location" behaviour of a 303, set it by hand:

    ```python
    res.status = 303
    res.headers = 'Location', '/orders/1'
    ```

## Files

```python
res.file('images/cat.jpg')                                  # inline
res.file('reports/q1.pdf', filename='Q1_Report.pdf')        # force download
```

The content type is guessed from the extension and the file is streamed with `aiofiles`, so a large file doesn't load into memory or block the loop.

### Confining the read with `within`

`res.file()` serves whatever path you hand it, which is fine for a constant you wrote and not fine once any part of the path comes from the request. Pass `within` to confine the read to a single directory:

```python
def download(req, res, ctx):
    res.file(req.params.get('name'), within='/var/lib/app/uploads')
```

The path is fully resolved before the file is opened, and anything landing outside the root returns 404. That covers `..` segments, absolute paths pointing elsewhere, and symlinks leaving the tree. `..` segments that stay inside still resolve normally. The root can be anywhere the process can reach, not just inside your project.

[**Serving Files**](files.md) covers the whole surface: choosing a root, access-controlled downloads, how this relates to `app.ASSETS()`, and what is deliberately left out.

!!! warning "No range requests or caching headers"
    `res.file()` sends no `ETag`, `Last-Modified`, `Content-Length`, or `Accept-Ranges`. Browsers cannot resume, seek within, or conditionally re-request the file, which rules it out for video seeking. Serve large static assets from Nginx or a CDN and keep `res.file()` for small or access-controlled downloads.

## Streaming

Hand `res.stream()` an async generator to send a response in chunks:

```python
async def report(req, res, ctx):
    async def rows():
        yield 'id,name\n'
        async for row in db.cursor('SELECT id, name FROM users'):
            yield f'{row.id},{row.name}\n'

    res.stream(rows(), content_type='text/csv')
```

### Server-sent events

```python
res.stream(events(), sse=True)
```

!!! danger "SSE currently emits a bytes repr"
    With `sse=True`, Heaven serializes each item and then string-formats it, so the wire output is `data: b'{"i": 0}'` — the Python `bytes` prefix and quotes included. Browsers will not parse that as JSON.

    Until it's fixed, format the frames yourself and stream them as plain text:

    ```python
    async def events():
        while True:
            payload = orjson.dumps(await queue.get()).decode()
            yield f'data: {payload}\n\n'

    res.stream(events(), content_type='text/event-stream')
    ```

## Work that outlives the response

`res.defer()` schedules a callback to run **after** the response has been sent — right for a job too small to justify a queue.

```python
async def send_receipt(app):
    await mailer.send(...)

async def checkout(req, res, ctx):
    res.body = {'status': 'ok'}
    res.defer(send_receipt)
```

The callback receives the **app**, not the request.

!!! warning "Deferred callbacks must be `async`"
    A sync function raises `TypeError` *after* the response has already gone out, where you cannot recover or report it. Capture what you need in a closure or `functools.partial`, and always define it with `async def`.

    Note also that deferred callbacks do **not** run under the [Earth](earth.md) test client.

## Aborting

`res.abort(body)` ends the request immediately:

```python
if user.is_banned:
    res.status = 403
    res.abort('Go away.')
```

!!! warning "Abort skips all AFTER hooks"
    Including Heaven's session-saving hook. Anything you rely on an `AFTER` hook to finish will not happen on an aborted request.

## Templates

`res.render()` renders a Jinja2 template into the body — covered in [Templates & Assets](html.md).

```python
await res.render('profile.html', user=user)
```

---

**Next:** HTML, CSS and everything a browser needs → **[Min 13-14 — Templates & Assets](html.md)**
