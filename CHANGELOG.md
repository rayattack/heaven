### 1.2.1
- **Feature**: **Smart CORS**. Re-architected `app.cors()` to accept flexible configurations.
    - **Kwargs Support**: Now accepts configuration via kwargs (e.g. `maxAge=3600`) with robust key normalization (handles `max-age`, `MAX_AGE`, `maxage`).
    - **Origins Array**: Fully supports passing an array of origins (e.g. `origin=['http://a.com', 'http://b.com']`). Automatically reflects the matching origin or `null` while setting `Vary: Origin`.
    - **Auto-Coercion**: Response headers (`methods`, `headers`) passed as lists are automatically joined into spec-compliant strings.
- **Security/Stability**: **Response Hardening**.
    - `Response.header()` now automatically coerces all values to string and joins list/tuple inputs. This prevents server crashes when developers accidentally pass non-string types to headers.

### 1.2.0
- **Feature**: **Schema Grouping**. Introduced intuitive grouping for OpenAPI documentation.
    - **Auto-Grouping**: Endpoints are automatically tagged based on their URL path (e.g., `/users/:id` -> `Users`).
    - **Explicit Grouping**: Added `group` parameter to schema definitions to override auto-grouping (e.g., `group='Orders'`).
- **Cleanup**: **Metadata API**.
    - Removed `title` parameter from schema definitions to reduce redundancy.
    - Standardized on `summary` (short description) and `description` (long markdown).

### 1.1.0
- **Feature**: **Guardian Angel 2.0**. A completely redesigned global proper debug page.
    - Catches **all** unhandled exceptions when `debug=True`.
    - Displays rich traceback, request details (headers, params, IP), and environment info.
    - Zero dependencies (removed Bulma CDN), works offline with beautiful dark mode UI.

### 1.0.1
- **Fix**: Automatically serialize `dict` and `list` responses to JSON even when no schema is defined, preventing ASGI errors.

### 1.0.0
- **Core Features**: Added `app.cors()` and `app.sessions()` directly to the Router.
- **Context DX**: Added support for dot-notation assignment on Context (`ctx.user = ...`).
- **Context Protection**: Reserved keys (like `ctx.session`) are now protected from accidental overwrite.
- **Security**: Added `heaven.security` module for strictly typed, signed serialization.
- **Breaking Change**: Removed `req.session` in favor of `ctx.session`.
- **Docs**: Comprehensive "Going to Production" guide added.

### 0.6.0
- **Schema Validation**: Added `router.SCHEMA` and `req.data` for robust input validation.
- **OpenAPI**: Added `router.DOCS()` for zero-config Swagger UI generation.
- **File Serving**: Added `res.file()` for streaming files.

### 0.5.1
- **Typing**: Added more support for typing and type hints.
- **Fix**: Parameters should be processed correctly.

### 0.5.0
- **URI Parsing**: Major change to the underlying engine and how Heaven parses URIs.
- **Routing**: Support for flexible parameter labels (e.g., `/v1/profiles/:id/orders` and `/v1/profiles/:identity` simultaneously).

### 0.4.2
- **Param Hints**: Added support for specifying data types for automatic parameter parsing.
- **Daemons**: Added `app.daemon` for background tasks.

### 0.3.10
- **IP Object**: Added `req.ip` object property (provides `ip.address` and `ip.port`).

### 0.3.9
- **Template Injection**: Automatically inject `Request`, `Response`, and `Context` into Jinja2 template scope.
- **Testing**: Added support for using mock Heaven objects.

### 0.3.8
- **Interpolation**: Added `response.interpolate(name, **contexts)` to render HTML without saving to `res.body`.

### 0.3.7
- **Cookies**: Added `response.cookie(name, value, **kwargs)` with support for all valid Set-Cookie parameters.

### 0.3.6
- **Websockets**: Changed ASGI websocket response from `websocket.start` to `websocket.http.response.start`.

### 0.3.5
- **Global State**: Added support for `app._.` lookup helper paradigm for global state management.

### 0.3.4
- **Deferred Calls**: Added `heaven.call` to inject Heaven instance into external modules.

### 0.3.3
- **Query Strings**: Fixed bug with query string handling and edge cases.

### 0.3.2
- **Error Messages**: Improved error messages for debugging (e.g., UrlDuplicateError details).
- **Request**: Added `.host` and `.scheme` retrieval from the request object.
- **CLI**: Implemented `Application.listen` for `python app.py` execution.

### 0.3.1
- **Daemons**: Added support for lifecycle daemons via `Application.daemons`.

### 0.2.6
- **Response**: Added `Response.out` helper for single-function status/body/headers setting.

### 0.1.0
- **Fix**: Cookie partitioning logic for strings containing `=`.
- **Rendering**: Added synchronous rendering support.
- **Response**: Removed unimplemented `Response.file` method.
- **Callables**: Added support for deferred callables receiving `Application | Router`.
- **Lifecycle**: Introduced `router.ONCE` for startup/shutdown hooks.

### 0.0.9
- **Fix**: Exception handling to ignore HTTP cookie malformation errors.

### 0.0.8
- **Fix**: Bug where params caused images not to load due to route traversal.
- **Fix**: Parameterization of querystring when `:dynamic` param exists.

### 0.0.7
- **Mounting**: Added mount isolation support for router aggregation.

### 0.0.5
- **Cleanup**: Removed unnecessary comments.

### 0.0.4
- **Routing**: Added parameterization support for wildcard routes.

### 0.0.3
- **Request**: Added support for `str` to `bytes` encoding in `req.body`.
- **Dispatch**: Changed how single dispatch works on body.
- **Fix**: Router wildcard typo fix.
- **Fix**: No deviation handling for parameterized/wildcard routes.

### 0.0.2
- **Cleanup**: Removed unused variables.

### 0.0.1
- **Initial Release**
