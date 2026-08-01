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
