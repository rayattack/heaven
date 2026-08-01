# Serving Files

`res.file()` streams a file from disk to the client. It guesses the content type, sets a `Content-Disposition`, and reads the file in chunks with `aiofiles` so a large file neither loads into memory nor blocks the event loop.

```python
async def logo(req, res, ctx):
    res.file('images/logo.png')
```

This page covers the whole surface: what gets sent, how to confine a read to one directory with `within`, how that relates to `app.ASSETS()`, and what `res.file()` deliberately does not do.

## The basics

```python
res.file('images/cat.jpg')                              # inline, browser renders it
res.file('reports/q1.pdf', filename='Q1_Report.pdf')    # download, browser saves it
res.file('video.mp4', chunk_size=65536)                 # larger read buffer
```

**Parameters:**

| Name | Default | Meaning |
| :--- | :--- | :--- |
| `filepath` | required | The file to send. Relative to `within` when that is given, otherwise used as-is. |
| `filename` | `None` | Send as an attachment under this name. Omit for inline display. |
| `chunk_size` | `4096` | Bytes read per iteration while streaming. |
| `within` | `None` | Confine the read to this directory. See [below](#confining-a-read-with-within). |

## What gets sent

On success the response is a `200` with the file streamed as the body:

| Header | Value |
| :--- | :--- |
| `Content-Type` | Guessed from the extension, falling back to `application/octet-stream` |
| `Content-Disposition` | `inline; filename="<basename>"`, or `attachment; filename="<filename>"` when you pass `filename` |

Any of the following produce a `404` with the body `File not found` and no content headers:

- the path does not exist
- the path is a directory, so there is no directory listing to leak
- the path resolves outside `within`, when `within` is given
- `within` itself does not exist

!!! note "No `Content-Length` is sent"
    The body is streamed, and Heaven does not stat the file first, so responses are chunked without a declared length.

## Confining a read with `within`

`res.file()` on its own serves exactly the path you hand it. That is the right behaviour for a low-level primitive, and it is fine when the path is a constant you wrote. It stops being fine the moment any part of the path comes from the request:

```python
async def download(req, res, ctx):
    res.file(f"uploads/{req.params.get('name')}")   # a name of ../../etc/passwd escapes uploads/
```

Passing `within` fixes that by confining the read to one directory:

```python
async def download(req, res, ctx):
    res.file(req.params.get('name'), within='/var/lib/app/uploads')
```

### The rule

Both the root and the requested path are fully resolved before anything is opened, and the read only proceeds if the result sits inside the root. Resolution happens at the filesystem level rather than by inspecting the string, which is why it holds regardless of how the path was spelled.

!!! tip "Why resolution beats pattern matching"
    Rejecting paths that literally contain `..` looks equivalent and is not. The ASGI `path` reaches your handler already percent-decoded, so `%2e%2e` and `..%2f` arrive as `..` after any string filter has run, and tricks like `....//` collapse to the same place. Resolving the path first means every spelling of "outside the root" ends up at the same comparison.

### Choosing a root

`within` is a directory, not a project-relative name, and it can be anywhere the process can reach:

```python
res.file(name, within='/var/lib/app/uploads')     # absolute, used as given
res.file(name, within='/mnt/nfs/media')           # a mounted share
res.file(name, within='uploads')                  # relative, resolved against the working directory
```

A relative root resolves against the **working directory**, which is wherever the process was started rather than where your module lives. If that distinction matters, anchor it explicitly:

```python
from os import path

UPLOADS = path.join(path.dirname(path.realpath(__file__)), 'uploads')

async def download(req, res, ctx):
    res.file(req.params.get('name'), within=UPLOADS)
```

### Two ways to pass the path

`filepath` may be relative to `within`, or the full path to a file beneath it. Both forms mean the same thing, so you can build the path yourself and still get the check:

```python
res.file(name, within=UPLOADS)                    # resolved against the root
res.file(path.join(UPLOADS, name), within=UPLOADS)  # already absolute, still verified
```

### What is rejected

Given `within='/srv/media'`:

| Requested | Result |
| :--- | :--- |
| `clips/intro.mp4` | served from `/srv/media/clips/intro.mp4` |
| `clips/../intro.mp4` | served, because it stays inside the root |
| `../secrets.env` | 404 |
| `../../../../etc/passwd` | 404 |
| `/etc/passwd` | 404, an absolute path outside the root does not override it |
| a symlink in the root pointing to `/etc/passwd` | 404, symlinks are resolved before the check |
| `/srv/media-private/notes.txt` | 404, a sibling sharing the name prefix is still outside |

The last two are the cases a hand-rolled check usually misses. Symlinks only reveal themselves once the path is resolved, and a prefix comparison that forgets the trailing separator treats `/srv/media-private` as living inside `/srv/media`.

!!! warning "`within` is opt-in"
    Omitting it leaves the path unconfined, which is unchanged behaviour and correct for trusted, hard-coded paths. Add it whenever the path is derived from the request, including indirectly through a database lookup keyed on user input.

## Access-controlled downloads

`within` answers "can this path be read", not "may this caller read it". Authorisation stays your handler's job, and the two compose:

```python
from os import path

INVOICES = path.join(path.dirname(path.realpath(__file__)), 'invoices')

async def invoice(req, res, ctx):
    invoice_id = req.params.get('id')

    record = await ctx.db.fetchrow(
        'SELECT filename FROM invoices WHERE id = $1 AND account = $2',
        invoice_id, ctx.account_id,
    )
    if not record:
        res.status = 404
        res.body = b'Not found'
        return

    res.file(record['filename'], filename=f'invoice-{invoice_id}.pdf', within=INVOICES)
```

The ownership check decides whether this account may see the invoice at all. `within` guarantees that whatever `filename` turns out to hold, the read cannot leave `invoices/`, which matters because that value came out of a database rather than out of your source.

## Relationship with `app.ASSETS()`

`app.ASSETS()` is a thin wrapper that registers a wildcard route and calls `res.file(..., within=<the asset folder>)` for you:

```python
app.ASSETS('assets')                            # serves ./assets at /assets/*
app.ASSETS('assets', relative_to=__file__)      # anchored to the module, not the cwd
```

The containment guarantees are identical, since it is the same code path. Reach for `ASSETS` when you want a whole folder mounted at a url prefix, and for `res.file()` when individual reads need a handler around them, whether for authorisation, logging, or a computed filename.

## Receiving uploads

Sending a file out is only half of it. On the way in, Heaven reads the whole request body before your handler runs, because `req.body`, `req.json` and `req.form` are ordinary properties that have to already have the data. That is the right trade for a JSON payload and the wrong one for a large file.

### Cap what a buffered route will accept

```python
app = App(max_body_size=10 * 1024 * 1024)   # 10MB
```

A request whose body goes past the cap gets `413 Payload too large`, and Heaven **stops keeping** the body at that point. Memory holds at the ceiling no matter how much more is sent, which is the point of the setting: it bounds what a single request can cost you, rather than checking the size once everything is already in memory.

Heaven does keep *reading* past the limit, discarding as it goes. That is deliberate. Answering mid-upload while the client is still sending resets the connection, and the client sees a broken pipe instead of the reason it was refused. Draining costs bandwidth but nothing in memory, and it means the `413` actually arrives.

!!! warning "There is no cap unless you set one"
    `max_body_size` defaults to `None`, meaning unlimited, so that upgrading does not start rejecting uploads that used to work. Set it for anything reachable from the internet, and keep a matching `client_max_body_size` in your proxy so oversized requests die before they reach Python at all.

### Stream large uploads instead of buffering them

Register the route with `stream=True` and the body is left unread, so your handler can consume it in chunks and write each one straight to its destination:

```python
from aiofiles import open as async_open

app.POST('/upload', receive, stream=True)

async def receive(req, res, ctx):
    async with async_open('/var/lib/app/uploads/incoming.bin', 'wb') as f:
        async for chunk in req.stream():
            await f.write(chunk)
    res.body = {'ok': True}
```

Peak memory is one chunk regardless of upload size. An 80MB upload through a streaming route costs about 36KB of Python heap, against roughly 160MB buffered.

A streaming route is a different contract, so the two halves do not mix:

- `req.body` and `req.json` raise on a streaming route, because nothing was buffered for them to read.
- `req.form` works on a streaming route, but it must be awaited: `form = await req.form`. See [the next section](#parse-a-form-without-buffering-it).
- `req.stream()` raises on a normal route, because the body was already read and is sitting on `req.body`.
- The body arrives once and is not retained, so it can only be consumed once: by `req.stream()` or by awaiting `req.form`, not both.

!!! note "`max_body_size` does not apply to streaming routes"
    A streaming route exists precisely to accept things larger than the cap, and it is your handler that decides how much to accept. Count the bytes as you write them and stop when you have had enough:

    ```python
    async def receive(req, res, ctx):
        written = 0
        async with async_open(target, 'wb') as f:
            async for chunk in req.stream():
                written += len(chunk)
                if written > LIMIT:
                    res.status = 413
                    return
                await f.write(chunk)
    ```

### Parse a form without buffering it

The most common reason to want streaming is a file upload, and file uploads usually arrive as `multipart/form-data` with fields alongside the file. On a streaming route, `await req.form` parses the body incrementally as it arrives:

```python
app.POST('/upload', receive, stream=True)

async def receive(req, res, ctx):
    form = await req.form

    form.get('title')                   # fields work as usual
    video = form.get('video')           # a File object
    video.save('/var/lib/app/uploads/incoming.bin')
    res.body = {'ok': True, 'size': video.size}
```

Field values are held in memory, capped at 1MB each. File parts are written to a spooled temporary file as they arrive: below 256KB they stay in memory, above it they move to disk, so a 20MB upload peaks at a few hundred KB of Python heap instead of hundreds of MB. The temp file is cleaned up automatically when the request is garbage collected; call `.save(path)` to keep the upload.

A streamed `File` offers more than `.content`:

- `.filename` and `.content_type`: what the client declared.
- `.size`: bytes received for this part.
- `.save(path)`: copy to a destination in chunks, never holding the whole file.
- `.file`: a file object positioned at the start, for handing to anything that reads files.
- `.content`: still the whole file as bytes. It reads a spilled part back off disk, so reach for `.save()` or `.file` instead for anything large.

Awaiting `req.form` on a buffered route is harmless (the form is parsed already and the await returns it unchanged), so handler code can be written one way and moved between the two kinds of route. Reading fields on a streaming route *without* awaiting raises a `RuntimeError` saying to await first.

The ceilings live in `heaven.form` as module constants: `FIELD_LIMIT` (1MB per field value), `SPOOL_LIMIT` (256KB before a file part moves to disk), `HEADERS_LIMIT` (16KB of headers per part) and `PARTS_LIMIT` (1000 parts). Set them before serving if your forms are unusual:

```python
import heaven.form
heaven.form.FIELD_LIMIT = 8 * 1024 * 1024
```

A form that breaks a ceiling, or a multipart body that ends without its closing boundary, raises `ValueError`. Heaven drains the rest of the body before the error surfaces, for the same reason `max_body_size` does: answering mid-upload resets the connection, and draining first means the client actually receives the error response.

### Which one to use

| Situation | Approach |
| :--- | :--- |
| JSON, form fields, a small avatar | Default buffering, with `max_body_size` set |
| Video, backups, anything unbounded | `stream=True` and write it as it arrives |
| A form with fields and a large file | `stream=True` and `await req.form` |
| Uploads from the public internet | Both: a cap on normal routes, streaming where large files are expected |

## What `res.file()` does not do

!!! warning "No range requests or caching headers"
    No `ETag`, `Last-Modified`, `Content-Length`, or `Accept-Ranges` is sent. Clients cannot resume a broken transfer, seek within a file, or make a conditional re-request, which rules this out for video scrubbing.

Serve large or heavily requested static files from Nginx, Caddy, or a CDN, which handle all of the above and do it faster. Keep `res.file()` for small files and for downloads that need a handler in front of them.

## Testing it

Earth drives the real handler, and consumes the streamed body so you can assert on it directly:

```python
class DownloadTest(IsolatedAsyncioTestCase):
    async def test_confined_to_the_upload_folder(self):
        async with app.earth.test() as earth:
            req, res, ctx = await earth.GET('/download/report.pdf')
            self.assertEqual(res.status, 200)

            req, res, ctx = await earth.GET('/download/../../../etc/passwd')
            self.assertEqual(res.status, 404)
```

Write the escape case as a test rather than checking it by hand once. It is the kind of guarantee that a later refactor can quietly remove.
