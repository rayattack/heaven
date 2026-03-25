### 1.3.14
- **Feature**: **Method-Scoped Hooks**. `BEFORE()` and `AFTER()` now accept a `methods` parameter to restrict hooks to specific HTTP methods. Schema validation and output hooks are now automatically scoped to their registered method, preventing e.g. a POST validation hook from running on GET requests.
- **Feature**: **Template Prefix & Merging**. `TEMPLATES()` now accepts a `prefix` parameter for namespaced template loading via Jinja2 `PrefixLoader`. Multiple `TEMPLATES()` calls merge loaders via `ChoiceLoader` instead of overwriting. Mounted sub-apps preserve their template prefixes.
- **Feature**: **Mounted WebSocket Handlers**. `mount()` now correctly delegates WebSocket routes using the `(sender, receiver, req, ctx)` signature instead of the HTTP `(req, res, ctx)` signature.
- **Feature**: **Docs Favicon**. `DOCS()` and `SubdomainContext.doc()` now accept a `favicon` parameter to set a custom favicon on the generated API reference page.
- **Improved**: **WebSocket `receiver()` Robustness**. The internal `receiver()` closure now loops over ASGI messages, properly handling `websocket.disconnect` by returning `None` and only yielding data on `websocket.receive`.
- **Improved**: **Subdomain CORS & Sessions**. `cors()` and `sessions()` now accept a `subdomains` parameter and automatically register `OPTIONS` wildcard handlers per subdomain. Sessions now delegate to `res.cookie()` with sensible defaults.
- **Improved**: **`SubdomainContext` Consistency**. Renamed `assets` to `ASSETS` to match the uppercase convention. Added `cors()` proxy method.
- **Fix**: **`listen()` Port Type**. `port` parameter is now typed as `int` (was `str`).
- **Fix**: Removed invalid `websocket.http.response.start` send after WebSocket handler completion.

### 1.3.13
- **Feature**: **Livereload**. When `debug=True`, Heaven automatically injects a livereload script into HTML responses from `res.render()` and `res.renders()`. A WebSocket endpoint at `/__heaven/livereload` detects server restarts and triggers a browser reload. Zero config — on by default in debug, absent in production.
- **Fix**: **WebSocket `receiver()` Skips Non-Message Types**. The internal `receiver()` closure now loops over ASGI messages, only returning on `websocket.receive` (data) or `websocket.disconnect` (`None`). Previously, unconsumed `websocket.connect` messages in the receive queue would be returned as `None`, causing handlers to exit immediately.
- **Fix**: **WebSocket `__call__` Cleanup**. Removed invalid `websocket.http.response.start` send after a WebSocket handler completes. This ASGI message is only valid for rejecting a WebSocket upgrade before acceptance — sending it after a handled connection raised a `RuntimeError` in uvicorn.

### ~~1.3.12~~ (redacted — livereload caused infinite page reloads due to WebSocket bugs above)

### 1.3.11
- **Feature**: **Subdomain CORS**. `app.cors()` now accepts a `subdomains` parameter (list of subdomain names) to apply CORS to specific subdomains. Defaults to `["www"]`. Also added `cors()` to `SubdomainContext` so `api.cors(origins=[...])` works directly on subdomain proxies.

### 1.3.10
- **Fix**: **`res.cookie()` Directives Ignored**. Fixed bug where `res.cookie()` built the full cookie string with all directives (domain, httponly, samesite, etc.) but discarded it, only setting the bare `name=value` header.
- **Improved**: **Session Cookie Options**. `app.sessions()` now accepts `**cookie_opts` (e.g. `domain`, `secure`, `samesite`, `partitioned`) and delegates to `res.cookie()` instead of hardcoding the `Set-Cookie` string. Defaults: `path="/", httponly=True, samesite="Lax"`. Enables cross-subdomain sessions via `app.sessions("secret", domain=".example.com")`.

### 1.3.9
- **Documentation**: **`.heaven` LLM Context File**. Complete rewrite of the `.heaven` reference file covering all 23 framework APIs. Designed to enable LLMs to write idiomatic Heaven code using string discovery, middleware, schemas, subdomains, and more.
- **Documentation**: **`.pytastic` Update**. Updated pytastic reference to document `strip`, `partial`, and runtime validation options (`vx.validate(Schema, data, strip=True, partial=True)`).

### 1.3.8
- **Feature**: **Pytastic Integration**. Replaced internal schema validation with `pytastic` library. Single shared `Pytastic` instance per `Router` for validation caching and performance.
- **Feature**: **Output Protection via `strip`**. `protect=True` (default) now uses `pytastic.validate(..., strip=True)` to silently remove extra fields from responses. Prevents accidental data leaks (e.g., `password_hash`) without raising errors. Propagates to nested `List[TypedDict]` items.
- **Feature**: **Partial Responses**. `partial=True` uses `pytastic.validate(..., partial=True)` to allow responses to omit required schema fields. Useful for summary/list endpoints returning subsets of data.
- **Improved**: **Schema Baking**. Simplified `output_hook` in `_bake_schemas` — delegates `strip` and `partial` directly to `pytastic.validate()`, removing convoluted fallback logic.
- **Cleanup**: Removed `heaven/schema/` directory (replaced by `pytastic` re-export in `heaven/schema.py`). Removed stale comments from `router.py`.

### 1.3.6
- **Feature**: **Response HTTP Proxy**. Added `res.http` as a proxy for `http.HTTPStatus`. Now you can do `res.status = res.http.CREATED` without importing `HTTPStatus`.

### 1.3.5
- **Feature**: **Typed Context Key**. Added `Key[T]` for typed context storage and retrieval. usage: `app.keep(Key[User]("user"), user_obj)`.
- **Feature**: **Generic Request**. `Request` is now Generic, enabling typed `req.data` return values based on the schema.
- **Improved**: **Type Safety**. Enhanced typing support throughout the Router and Context, paving the way for better IDE autocompletion.

### 1.3.4
- **Feature**: **Smart Field**. Added `Field()` helper for schemas, abstracting msgspec constraints. Supports `min/max` (numeric), `min_len/max_len` (sequences), `format="email"`, and more. Pyright compliant.

### 1.3.1
- **Feature**: **Ordered Execution**. Hooks now run in strict FIFO order (Insertion Order).
- **Feature**: **Guard & Unwind**. Mounting logic updated for intuitive middleware layering:
    - **BEFORE (Guard)**: Parent hooks run *before* Child hooks.
    - **AFTER (Unwind)**: Child hooks run *before* Parent hooks.
- **Feature**: **Loop Monitor**. Added `App(monitor=0.1)` configuration to log warnings if the event loop is blocked (latency spike detection).
- **Documentation**: **Complete Overhaul**. Changed the documentation suite (30-Minute Mastery).

### 1.3.0
- **Feature**: **Subdomain Schemas**. Full support for defining schemas specific to subdomains.
    - **Proxy API**: New `app.subdomain('name')` API that returns a context-aware proxy.
    - **Isolation**: `app.subdomain('api').schema.POST(...)` registers schemas specifically for that subdomain, preventing collisions with main routes.
    - **Hooks**: Schema baking now respects subdomain boundaries (`BEFORE`/`AFTER` hooks are registered to the correct subdomain).
- **Fix**: **Pytest Compatibility**. Resolved issues with `async def` test discovery and global `mock` side-effects that were breaking test suites.
- **Fix**: **Crash Prevention**. hardened `_string_to_function_handler` against non-string inputs (like Mocks/Objects), resolving crashes during complex testing scenarios.

### 1.2.2
- **Feature**: **String Schemas**. `router.schema` methods (e.g. `POST`, `GET`) now accept string paths for `expects` and `returns` arguments.
    - **Lazy Loading**: You can now pass schemas as strings (e.g. `expects='my.module.Schema'`) to avoid circular imports and keep code clean, matching the behavior of route handlers.

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
