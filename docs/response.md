# The Response 🗣️

You have listened. Now you must speak. The `Response` object gives you the tools to reply with JSON, HTML, Files, or even silence.

The handler signature:

```python
async def handler(req, res, ctx):
    ...
```

## The Basics

- **`res.status`**: (int) The HTTP status code. Defaults to `200`.
- **`res.body`**: (bytes|str|dict|list) The content.

Wait, `dict`? Yes. If you register a schema, Heaven handles the encoding. If not, it assumes bytes/str.

```python
res.body = "Hello World" # Text
res.body = b"Hello World" # Bytes
```

### `res.http`

Instead of importing `HTTPStatus` from the standard library, you can use the built-in proxy:

```python
# No need for: from http import HTTPStatus
res.status = res.http.CREATED
if res.status == res.http.UNAUTHORIZED:
    ...
```

## JSON

```python
# Manual JSON
res.headers = 'Content-Type', 'application/json'
res.body = json.dumps({'msg': 'hi'})

# Heaven Helper (if using Schemas)
# Just return the object matching the schema, Heaven does the rest.
res.body = MyUserObject() 
```

## Headers

Headers are simple key-value tuples. You can add as many as you like.

```python
# Add one
res.headers = 'Content-Type', 'application/json'

# Add another
res.headers = 'X-Powered-By', 'Heaven'
```

## Helpers

### `res.redirect(location)`
Send the user somewhere else.

```python
res.redirect('https://google.com')
```

### `res.file(path, filename=None)`
Stream a file from disk. Heaven handles the content-type automatically.

```python
# Serve inline (e.g. image)
res.file('images/cat.jpg')

# Force download
res.file('reports/finance.pdf', filename='final_report.pdf')
```

### `res.abort(body)`
Stop everything immediately. No subsequent hooks will run.

```python
if user.is_banned:
    res.status = 403
    res.abort("Go away.")
```

### `res.defer(func)`
Run a task *after* the response has been sent to the user. This is great for tasks that shouldn't block the UI but aren't complex enough for a daemon.

```python
async def send_email(app):
    await email_service.send(...)

res.defer(send_email)
res.body = "Email queued!"
```

---

## Streaming & Files

Heaven makes it easy to stream large responses or serve files without blocking the server event loop.

### `res.stream(generator)`

Stream data chunk-by-chunk to the client. This is perfect for large datasets or real-time updates.

```python
async def large_report(req, res, ctx):
    async def generate():
        yield "Start of report\n"
        # Simulate heavy work
        for i in range(100):
            yield f"Row {i}\n"
    
    # Automatically sets Transfer-Encoding: chunked
    res.stream(generate())
```

#### Server-Sent Events (SSE)

You can also create an SSE stream easily:

```python
res.stream(event_generator(), sse=True)
```

### `res.file(path)`

Serve a file from the disk. Heaven uses `aiofiles` to stream the file efficiently, so even sending a 10GB file won't spike your RAM or block other requests.

```python
# Serve inline (e.g. an image)
res.file('/var/www/image.png')

# Force download
res.file('/var/www/report.pdf', filename='Annual_Report.pdf')
```

---

**Next:** How do we share data between the router, the request, and the response? On to **[The Context](context.md)**.