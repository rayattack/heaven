# Heaven Framework - API Specification

> **TL;DR**: Heaven is a high-performance, minimalist Python ASGI web framework focused on speed, simplicity, and purity. It uses explicit routing, centralized hooks (middleware), and a thin layer over ASGI.

## 1. Core Application (`App` / `Router`)

The `App` class (alias for `Router`) is the main entry point.

```python
from heaven import App
app = App()
```

### Routing Methods
Standard HTTP verbs are supported. Handlers are async or sync functions receiving `(req, res, ctx)`.

- `app.GET(route, handler)`
- `app.POST(route, handler)`
- `app.PUT(route, handler)`
- `app.DELETE(route, handler)`
- `app.PATCH(route, handler)`
- `app.WS(route, handler)` / `app.WEBSOCKET(route, handler)`

**Route Syntax:**
- Static: `/users`
- Parameterized: `/users/:id` (Access via `req.params['id']`)
- Wildcard: `/static/*` (Access via `req.params['*']`)

### Hooks (Middleware)
Middleware is implemented as "hooks" that run `BEFORE` or `AFTER` a request matches a route.

- `app.BEFORE(route, handler)`: Runs before the main handler.
- `app.AFTER(route, handler)`: Runs after the main handler.

**Note**: Hooks follow route matching logic. `app.BEFORE('/api/*', auth)` runs for all routes under `/api/`.

### Sub-Applications & Mounting
- `app.mount(other_app)`: Mounts another router/app.
- `app.subdomain('api')`: Registers a subdomain. Use `subdomain='api'` in route methods.

### Built-in Utilities
- `app.cors(origins="*", methods="*", ...)`: Enable CORS.
- `app.sessions(secret_key, ...)`: Enable cookie-based sessions (accessed via `ctx.session`).
- `app.daemons = async_func`: Register background tasks that run with the app.
- `app.listen(host, port)`: Run the app using Uvicorn.

---

## 2. Request (`req`)

The `Request` object provides access to incoming data.

- **Body**:
  - `req.body`: Raw bytes.
  - `req.json`: Parsed JSON dict (cached).
  - `req.data`: **Validated** (typed) data if a Schema was provided.
  - `req.form`: Parsed form data (multipart/urlencoded).

- **Parameters**:
  - `req.params`: Dictionary of route parameters (e.g., `:id`).
  - `req.queries`: Dictionary of query string parameters.
  - `req.headers`: Dictionary of request headers.
  - `req.cookies`: Dictionary of cookies.

- **Metadata**:
  - `req.method`: HTTP method (str).
  - `req.url`: Request path.
  - `req.ip`: Client IP.

---

## 3. Response (`res`)
The `Response` object is used to send data back to the client.

- **Sending Data**:
  - `res.text`: Send string.
  - `res.body = b'...'`: Set raw body.
  - `res.json`: Getter property. To send JSON, usually set `res.body` with dict (auto-encoded).
  - `res.status = 200`: Set HTTP status code.

- **Helpers**:
  - `res.abort(message, status=500)`: Immediately stop processing and send error.
  - `res.header(key, value)` / `res.headers = key, value`: Set headers.
  - `res.cookie(name, value, ...)`: Set cookies.
  - `res.redirect(url)`: Redirect client.
  - `res.file(path)`: Stream a file.
  - `res.stream(generator)`: Stream data from an async generator.

- **Templating**:
  - `app.TEMPLATES(folder)`: Enable templating (Jinja2).
  - `await res.render(template_name, **context)`: Render and send HTML.

---

## 4. Context (`ctx`)
A mutable dictionary-like object to pass data between hooks and handlers.

- `ctx.keep(key, value)`: Store data.
- `ctx.peek(key)`: Retrieve data.
- `ctx.user = ...`: Dot access is also supported for convenience.
- `ctx.session`: Access session data (if `app.sessions` enabled).

---

## 5. Schema & Validation (`app.schema`)
Heaven has built-in support for validation and OpenAPI generation using `msgspec`.

### Defining Schemas
Inherit from `heaven.Schema` (which is a `msgspec.Struct`).

```python
from heaven import Schema

class CreateUser(Schema):
    name: str
    age: int
```

### Registering with Validation
Use `app.schema` methods to register routes with schemas.

- `app.schema.POST('/users', expects=CreateUser, returns=UserResponse)`

- **expects**: Validates request body -> available at `req.data`.
- **returns**: keys response body to match schema.
- Automatic 422 Unprocessable Entity on validation failure.

### Generating Docs
- `app.DOCS('/docs')`: Serves an interactive API reference (Scalar) at `/docs`.
- Generates `openapi.json` automatically based on registered schemas.

---

## Example Usage

```python
from heaven import App, Schema

app = App()

# Schema
class Item(Schema):
    name: str
    price: float

# Register Handler
async def create_item(req, res, ctx):
    # req.data is typed as Item
    item = req.data 
    res.body = {"message": f"Created {item.name}"}

app.POST('/items', create_item)

# Register with validation (Sidecar pattern)
app.schema.POST('/items', expects=Item)

# Docs
app.DOCS('/docs')

if __name__ == "__main__":
    app.listen()
```
