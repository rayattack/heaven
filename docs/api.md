# Heaven API Reference 📖

A comprehensive guide to every method, property, and constant in the Heaven framework.

## App / Router
The central orchestrator of your application.

### `App()` / `Router(protect_output=True, ...)`
Initialize the framework. 
- `protect_output`: (Default `True`) Enables `msgspec` validation/projection.
- `fail_on_output`: (Default `False`) Determines if individual validation errors should crash the request or just log a warning.

### Routing Methods
All methods follow the signature: `(url: str, handler: Callable, subdomain: str = DEFAULT)`
- **`GET`, `POST`, `PUT`, `DELETE`, `PATCH`, `HEAD`, `OPTIONS`, `CONNECT`, `TRACE`**
- **`HTTP(url, handler)`**: Registers all the above methods at once.
- **`SOCKET(url, handler)`**: Registers a WebSocket handler.

### Hooks & Lifecycle
- **`BEFORE(url, handler)`**: Runs before matching routes.
- **`AFTER(url, handler)`**: Runs after matching routes.
- **`ON(event, handler)`**: Lifecycle hooks for `STARTUP` and `SHUTDOWN`.

### Utilities
- **`mount(url, other_router)`**: Nest applications.
- **`daemon(coroutine)`**: Register background tasks that run with the server lifecycle.
- **`listen(host, port)`**: shortcut for `uvicorn.run`.
- **`openapi()`**: Generates the OpenAPI spec dictionary.
- **`DOCS(url)`**: Serves the Swagger/OpenAPI UI.

---

## Request (`req`)
The object representing an incoming HTTP or WebSocket request.

- **`req.app`**: Access the parent `Router` instance.
- **`req.method`**: `str` (GET, POST, etc.)
- **`req.url`**: `str` (Relative path)
- **`req.headers`**: `dict`-like access to headers.
- **`req.cookies`**: Parsed `dict` of cookies.
- **`req.params`**: `dict` of URL parameters (e.g., `:id`).
- **`req.queries`**: `dict` of query string parameters.
- **`req.json`**: Body decoded via `msgspec`.
- **`req.data`**: Validated/Structured body data (if `Schema` is used).
- **`req.form`**: Parsed `multipart` or `urlencoded` data.
- **`req.ip`**: Client IP address info.
- **`req.subdomain`**: Current subdomain string.

---

## Response (`res`)
Used to send data back to the client. All methods return `self` for chaining.

- **`res.status = 200`**: Set HTTP status code.
- **`res.body = "data"`**: Set the response body.
- **`res.json()`**: Returns/sets body as JSON.
- **`res.text()`**: Returns/sets body as text.
- **`res.header(key, val)`**: Set a header.
- **`res.cookie(key, val, ...)`**: Set a cookie.
- **`res.renders(template, **data)`**: Render a Jinja2 template.
- **`res.file(path)`**: Serve a static file.
- **`res.stream(gen, sse=False)`**: Stream an async generator (with optional SSE formatting).
- **`res.abort(body=None)`**: Stop execution and return immediately.

---

## Context (`ctx`)
Shared state container for the duration of a request.

- **`ctx.keep(key, val)`**: Store a value.
- **`ctx.peek(key)`**: Retrieve a value.
- **`ctx.unkeep(key)`**: Remove and return a value.
- **`ctx.something`**: Property-style access to kept values.

---

## Earth
The integration testing engine. Access via `router.earth`.

- **`earth.GET(url, ...)`** / **`earth.POST(...)`**: Simulate requests.
- **`earth.upload(url, files=...)`**: Multipart upload helper.
- **`earth.SOCKET(url)`**: WebSocket simulation client.
- **`earth.test(track_session=True)`**: Context manager for full lifecycle + session tests.
