# Heaven API Reference

## `heaven.router`

### `Router` (alias `App`)
The core application class that manages routing, configuration, and lifecycle.

```python
class Router(configurator=None, protect_output=True, allow_partials=False,
             fail_on_output=True, debug=True, monitor=None)
```

**Parameters:**
- `configurator` (Callable | dict, optional): Configuration source, read back via `app.CONFIG(key)`.
- `protect_output` (bool): Strip undeclared fields from responses validated by a `returns` schema. Default `True`.
- `allow_partials` (bool): Allow partial response payloads. Default `False`.
- `fail_on_output` (bool): Return 500 when a response fails its `returns` schema, instead of sending it anyway. Default `True`.
- `debug` (bool): Serve the Guardian Angel error page on unhandled exceptions. Default `True`.
- `monitor` (float, optional): Warn when the event loop is blocked for longer than this many seconds. Off by default.

!!! danger "`debug=True` is the default"
    The debug error page includes the exception message and full traceback. Pass `debug=False` in production — see [Security](security.md#turn-off-debug-in-production).

**Properties:**
- `daemons`: (write-only) Register a background task.
- `earth`: (read-only) Lazy-loaded instance of `heaven.earth.Earth` testing engine.
- `ws`: (read-only) WebSocket status indicator.
- `_`: (read-only) Access to internal buckets via `Look` interface.

**Methods:**
- `abettor(method, route, handler, subdomain=DEFAULT, router=None)`: Internal method for registering routes.
- `call(handler, *args, **kwargs)`: Execute a handler string (dot-notation) with the app as context.
- `cors(handler=None, subdomains=None, **kwargs)`: Enable CORS. Recognised keys — `origin`/`origins`, `methods`, `headers`, `expose`, `credentials`, `max_age` (casing and separators are normalised). Defaults to fully permissive.
- `keep(key, value)`: Store value in application scope.
- `listen(host='localhost', port='8701', debug=True, **kwargs)`: Start the server using Uvicorn. **Broken on uvicorn ≥ 0.15** — it forwards a removed `debug` argument and raises `TypeError`. Use the `heaven run` CLI instead.
- `mount(router, isolated=True)`: Mount another `Router` instance. `isolated` determines if configs/buckets are merged.
- `peek(key)`: Retrieve value from application scope.
- `plugin(plugin_instance)`: Register a plugin (must have `install(app)` method).
- `sessions(secret_key, cookie_name="session", max_age=3600, subdomains=None, **cookie_opts)`: Enable signed cookie sessions. Extra keyword arguments are passed through to the cookie (`secure`, `samesite`, `domain`, `path`, …).
- `subdomain(subdomain)`: Initialize a new subdomain route engine.
- `unkeep(key)`: Remove and return value from application scope.
- `websocket()`: Enable WebSocket support (flag).

**Routing Shortcuts:**

All take `(route, handler, subdomain='www')`.

- `GET`, `POST`, `PUT`, `PATCH`, `DELETE`, `OPTIONS`, `CONNECT`, `TRACE`
- `SOCKET(url, handler)` — WebSocket handler. Aliases: `WS`, `WEBSOCKET`.
- `HTTP(url, handler)` — registers the handler for `CONNECT`, `DELETE`, `GET`, `OPTIONS`, `PATCH`, `POST`, `PUT` and `TRACE`.

!!! warning "There is no `HEAD()` method"
    `HEAD` is not registrable through any shortcut and `HTTP()` skips it, so a `HEAD` request to a `GET` route returns 404. The only way to serve one is the low-level `app.abettor('HEAD', route, handler)`.

    Relatedly: a method mismatch returns **404, not 405**, and `OPTIONS` is only answered if you call `app.cors()`.

**Hooks:**
- `BEFORE(url, handler)`: Pre-request middleware.
- `AFTER(url, handler)`: Post-request middleware.
- `ON(event, handler)`: Lifecycle hooks (`'startup'`, `'shutdown'`).

---

### `Route`
Internal node class representing a single route segment or endpoint.

```python
class Route(route, handler, router)
```

**Attributes:**
- `heaven_instance`: Reference to the parent `Router`.
- `parameterized`: Dictionary of parameters at this node.
- `queryhint`: Query string hints.
- `route`: The path segment.
- `handler`: The callable handler (if this is an endpoint).
- `children`: Dictionary of child `Route` nodes.

**Methods:**
- `match(routes, r)`: Traversing method to find a matching handler for a deque of route segments.
- `not_found(r, w, c)`: Default 404 handler.

---

### `Routes`
Internal collection class managing the route tree for a specific subdomain.

```python
class Routes()
```

**Attributes:**
- `afters`: Dictionary of AFTER hooks.
- `befores`: Dictionary of BEFORE hooks.
- `cache`: Flat cache of registered routes for fast lookup `{METHOD: {url: handler}}`.
- `routes`: The root nodes of the Radix-like tree.

**Methods:**
- `add(method, route, handler, router)`: Register a route. Handles splitting paths and creating `Route` nodes.
- `get_handler(routes)`: (Stub) Retrieve handler.
- `handle(scope, receive, send, metadata, application)`: Main ASGI request handling logic. Orchestrates `Request`, `Response`, `Context`, and middleware execution.
- `remove(method, route)`: Unregister a route.
- `xhooks(hookstore, matched, r, w, c)`: Execute hooks for a matched route.

---

### `Parameter`
Internal class for handling URL parameters.

```python
class Parameter(value, potentials)
```

**Methods:**
- `resolve(parameter_address)`: Resolves the parameter value based on the matched route structure, performing type casting if specified (e.g. `:id:int`).

---

### `SchemaRegistry`
Internal registry for route schemas.

**Methods:**
- `add(method, route, expects=None, returns=None, ...)`: Register schema metadata.
- `GET(...)`, `POST(...)`, etc.: Shortcuts for `add`.

---

## `heaven.request`

### `Request`
Represents an incoming HTTP or WebSocket request.

```python
class Request(scope, body, receive, metadata=None, application=None)
```

**Properties:**
- `app`: Parent `Router` instance.
- `body`: Raw request body (bytes).
- `cookies`: Dictionary of cookies.
- `data`: Validated/Typed request body (if schema present), else alias for `json`.
- `form`: `Form` instance (lazy loaded).
- `headers`: Dictionary of headers.
- `host`: Host header value.
- `ip`: Client IP access (`req.ip.address`).
- `json`: JSON decoded body.
- `method`: HTTP method.
- `mounted`: (Read/Write) Application this request was mounted from.
- `params`: URL path parameters.
- `qh`: (Read/Write) Query hints metadata.
- `queries`: Query string parameters.
- `querystring`: Raw query string.
- `route`: Matched route pattern.
- `scheme`: URL scheme.
- `server`: Server address.
- `subdomain`: Matched subdomain.
- `url`: Request URL path.

**Methods:**
- `stream()`: Async generator for request body (TODO).

---

### `Form`
Handles multipart/form-data and urlencoded parsing.

```python
class Form(req)
```

**Attributes:**
- `_data`: Dictionary of parsed data.

**Methods:**
- `get(name, default=None)`: Retrieve a field value.
- `to_dict()`: Return internal dictionary.
- `__getattr__(name)`: Attribute access to fields.

**Internal Methods:**
- `_parse(req)`
- `_parse_multipart(req, content_type)`
- `_parse_urlencoded(req)`

---

## `heaven.response`

### `Response`
Handles sending data back to the client.

```python
class Response(app, context, request)
```

**Properties:**
- `body`: Response body (bytes, str, dict, list).
- `deferred`: Boolean indicating if tasks are deferred.
- `headers`: List of headers.
- `metadata`: ASGI response metadata.
- `status`: HTTP status code (int).
- `template`: (Write-only) Template path.

**Methods:**
- `abort(payload)`: Abort execution with payload.
- `cookie(name, value, **kwargs)`: Set cookie. Supports `max_age`, `expires`, `httponly`, `samesite`, `secure`, `domain`, `path`, `partitioned`.
- `defer(func)`: Register an async task to run after response is sent.
- `file(filepath, filename=None, chunk_size=4096)`: Stream a file.
- `header(key, val)`: Add a header.
- `interpolate(name, **contexts)`: Async template rendering (returns string).
- `json()`: Decode body as JSON (if body is dict/list, returns it).
- `out(status, body, headers=None)`: Set status, body, and headers at once.
- `redirect(location, permanent=False)`: Send redirect response.
- `render(name, **contexts)`: Async render template to body.
- `renders(name, **contexts)`: Sync render template to body.
- `stream(generator, content_type='text/plain', status=200, sse=False)`: Stream from async generator.
- `text()`: Decode body as string.

---

### `MethodDispatch`
Internal decorator class for polymorphism in `Response` methods (like `abort`).

---

## `heaven.context`

### `Context`
Request-scoped state container.

```python
class Context(application)
```

**Methods:**
- `keep(key, value)`: Store value.
- `peek(key)`: Retrieve value.
- `unkeep(key)`: Remove and return value.

**Attributes:**
- Direct attribute access triggers `keep`/`peek`.
- Reserved keys: `session`, `app`, `request`, `response`, `headers`, `cookies`.

---

### `Look`
Wrapper class enabling dot-notation access for dictionaries (used for `ctx.session`).

---

## `heaven.schema`

Heaven validates with [pytastic](https://rayattack.github.io/pytastic/). There is **no `Schema` base class** — a schema is a plain `TypedDict` with `Annotated` constraint strings. See [Schemas & Validation](schema.md).

```python
from typing import Annotated, TypedDict

class User(TypedDict):
    name: Annotated[str, "min_len=2"]
    age:  Annotated[int, "min=18"]
```

**Re-exported from `heaven`:**

- `Pytastic`: the validator engine. Heaven keeps one instance per `Router`.
- `ValidationError`: raised on invalid data; caught internally and turned into a 422.
- `PytasticError`: base class for pytastic errors.

!!! warning "`Schema`, `Field` and `Constraints` do not exist"
    Earlier documentation described a msgspec-based `Schema` class with a `Field()` helper. That API was never part of this release — `from heaven import Schema` raises `ImportError`. Use `TypedDict` + `Annotated`.

---

## `heaven.earth`

### `Earth`
Testing engine.

```python
class Earth(app)
```

**Methods:**
- `bypass(middleware)`: Skip middleware during tests.
- `context()`: Create mock Context.
- `request(url, ...)`: Create mock Request.
- `response(req=None)`: Create mock Response.
- `swap(old_func, new_func)`: Mock dependencies.
- `test(track_session=True)`: Return `EarthContextManager`.
- `trio(url, ...)`: Return `(req, res, ctx)` tuple.
- `upload(url, files=..., data=...)`: Simulate multipart upload.
- `SOCKET(url)`: Return `MockSocket`.
- `GET`, `POST`, `PUT`, `DELETE`, `PATCH`...: Simulate requests.

---

### `EarthContextManager`
Context manager for tests. Handles installing/uninstalling hooks and swaps.

---

### `MockSocket`
Simulator for WebSocket connections.

**Methods:**
- `connect()`: Establish connection.
- `send(data)`: Send data to app.
- `receive(timeout=None)`: Receive data from app.
- `close(code=1000)`: Close connection.

---

## `heaven.utils` & `heaven.constants`

### `Lookup`
Dictionary wrapper for dot-notation access (used for `req.ip`).

### `preprocessor`
Internal function to parse ASGI scope and extract subdomain/headers.

### Constants
- **Methods**: `GET`, `POST`, `PUT`, `DELETE`, `PATCH`, `HEAD`, `OPTIONS`, `CONNECT`, `TRACE`, `SOCKET`.
- **Status**: `OK` (200), `CREATED` (201), `NOT_FOUND` (404).
- **Events**: `STARTUP`, `SHUTDOWN`.
- **Other**: `DEFAULT` ('www'), `WILDCARD` ('*').
