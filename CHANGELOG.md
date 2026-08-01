### 1.5.0

Correctness and hardening release. Three of these change observable behaviour: read
the first three entries before upgrading.

- **Breaking**: **`debug` Now Defaults To `False`**. `Router(debug=...)` previously defaulted to `True`, so any app constructed without the keyword served the Guardian Angel page on an unhandled exception, including the exception message and full traceback. The default is now `False`, which returns a plain `500 Internal Server Error` and logs the traceback instead. Pass `debug=True` explicitly for local development.
- **Breaking**: **BEFORE Hooks Run Broadest Pattern First**. `BEFORE` hooks previously ran exact-match registrations before wildcard ones, so a guard on `/*` executed *after* the route-specific hooks it was meant to precede. `BEFORE` now runs from the broadest matching pattern inward (`/*`, then `/users/*`, then `/users/:id`) and `AFTER` unwinds in the mirror order, so a pair registered on the same pattern brackets everything more specific. `AFTER`'s existing exact-before-global behaviour is preserved; only the relative order of nested wildcards changed. This matches what `.heaven` always documented.
- **Breaking**: **Method Mismatch Returns 405**. A request whose path matches a route registered under a different method returned 404. It now returns 405 with an `Allow` header listing the methods that path accepts. Paths matching no route still return 404.
- **Fix**: **Requesting A Prefix Of A Registered Route No Longer Raises**. With `/a/b/c` registered, a request for `/a/b` or `/a` walked the tree to an interior node and read `route`/`queryhint` off it, both of which are `None` there, raising `AttributeError` from `Route.match`. Because `match` is called before the request handling `try` block, the error skipped the framework's own 500 path entirely, discarding headers that BEFORE hooks had already set (CORS among them). Interior nodes are now treated as a miss and return 404. A second form of the same defect, where the prefix ran through a `:param` segment and failed in `Parameter.resolve`, is fixed by the same guard.
- **Fix**: **`ASSETS` Stays Inside Its Folder**. The requested path was joined onto the asset folder without normalisation, so `..` segments resolved outside it. Requests are now resolved with `realpath` and rejected with 404 unless they land inside the folder, which also covers absolute paths and symlinks pointing out of the tree. `..` segments that stay within the folder still resolve normally.
- **Fix**: **Mounted Children Keep Their Daemons**. `mount()` carried routes, hooks, schemas and lifecycle callbacks but not `__daemons`, so a daemon registered on a child was silently dropped and never started. Daemons are now carried onto the parent and start on its lifespan. Copying the list alone would have been wrong: `__rundaemons` calls `daemon(self)`, so a child's daemon would have been handed the *parent* app, and an isolated mount (the default) shares neither buckets nor configuration, meaning `app.peek('db')` inside it would read `None`. Daemons are therefore now bound to the router they were registered on, exactly as `ONCE` callbacks already were, and a child's daemon still receives the child. Apps that are not mounted are unaffected, since there the owner and the running app are the same object.
- **Feature**: **`res.file(..., within=...)`**. `res.file()` serves the path it is given, which is correct for a low-level primitive but unsafe when the path comes from the request. Passing `within` confines the read to one directory: the path is fully resolved first and anything landing outside returns 404, covering `..` segments, absolute paths pointing elsewhere, and symlinks leaving the tree. `within` is a directory anywhere the process can reach, not a project-relative name; absolute values are used as given and relative ones resolve against the working directory. `filepath` may be relative to `within` or the full path to a file beneath it. `app.ASSETS()` is now implemented on top of it, so there is one containment path rather than two.
- **Fix**: **Hook Method Scoping Is Per-Registration**. `methods=` wrote a `_hook_methods` attribute onto the handler function itself, so registering one function twice with different scopes applied the first scope to both, silently stopping the unscoped registration from running. The scope leaked across separate `App` instances for the same reason, and registering a bound method raised `AttributeError` because bound methods reject attribute assignment. Scoping is now stored per `(route, handler)` on the route engine. Registering the same pair twice unions the scopes, and an unscoped registration means every method.
- **Breaking**: **Route Path Parameters Support The Full Type Set**. `Parameter.resolve` only ever converted `:int` and `:str`. The other five names that query hints already accepted (`float`, `bool`, `date`, `datetime`, `uuid`) were parsed out of the route and then ignored, so `/report/:day:date` and `/item/:sku:uuid` registered without complaint and handed the handler a string. All seven now work identically in path segments and query hints, driven by a single `CONVERTERS` table in `heaven/utils.py` so the two surfaces cannot drift apart again. Three related changes come with it: a segment whose value cannot be converted no longer matches, so the request falls through to a covering wildcard or 404 instead of delivering an unconverted string; an unknown type name such as `:id:uuidd` now raises `UrlError` at registration rather than silently degrading to a string; and a parameter body with more than one colon (`:a:b:c`) previously produced the garbage key `a:b:c`, which is now rejected. Query string behaviour is deliberately unchanged, including its lenient boolean where an unreadable value reads as `False`.
- **Fix**: **OpenAPI Types For Every Path Parameter Kind**. Path parameters were typed as `integer` for `:int` and `string` for everything else. They now carry the right type and format per kind: `number` for `float`, `boolean` for `bool`, and `string` with `date`, `date-time` or `uuid` formats.
- **Feature**: **`HEAD` Is Supported**. `app.HEAD()` is now a registration shortcut, `app.HTTP()` includes `HEAD` in its fan-out, and a `HEAD` request with no explicit handler falls through to the matching `GET` route, returning its status and headers with an empty body.
- **Fix**: **OpenAPI Emits Path Parameters**. `app.openapi()` used heaven's own `/users/:id` route syntax as the OpenAPI path key and never emitted a `parameters` array, so path parameters did not render in Scalar. Paths are now rewritten to `/users/{id}` with a matching `parameters` entry per segment; a `:id:int` segment is typed as `integer`. Query hints are stripped from the documented path.
- **Fix**: **SSE Frames Carry The Payload**. `res.stream(..., sse=True)` interpolated the result of `orjson.dumps`, which is `bytes`, into an f-string, putting the bytes repr on the wire as `data: b'{"a":1}'`. Dict and list items are now decoded before framing, as are items a generator yields as raw bytes.
- **Fix**: **`app.listen()` Works Again**. It forwarded a `debug` argument that uvicorn removed years ago, raising `TypeError` on uvicorn 0.15 and later. `debug` now sets the app's own error-page mode and is not forwarded; remaining keyword arguments still pass through to `uvicorn.run`.
- **Tests**: 28 regression tests added in `tests/test_regressions.py` covering every item above. None of these paths had coverage before.
- **Docs**: New **Serving Files** reference page (`docs/files.md`) covering `res.file()` end to end: what it sends, confining a read with `within`, choosing a root inside or outside the project, access-controlled downloads, its relationship to `app.ASSETS()`, and the range/caching headers it deliberately omits. Linked from the Response, Templates & Assets, Security and API Reference pages.
- **Docs**: `.heaven`, `docs/hooks.md`, `docs/router.md`, `docs/api.md`, `docs/html.md`, `docs/response.md`, `docs/security.md`, `docs/deployment.md`, `docs/plugins.md`, `docs/snippets.md`, `docs/examples.md`, `docs/cli.md` and `docs/congrats.md` updated. Several of these described the defects above as known caveats, and `.heaven` documented the intended hook order rather than the actual one.

### 1.4.2
- **Fix**: **`orjson` Is Now A Declared Dependency**. `orjson` is imported by six modules (`router.py`, `request.py`, `response.py`, `security.py`, `earth.py`, `cli.py`) but was never listed in `pyproject.toml`, and none of the other declared dependencies pull it in transitively. A clean `pip install heaven` therefore produced a package that raised `ImportError` on `import heaven`. Now declared as `orjson = ">=3.0.0"`, the floor being 3.0 because `security.py` imports `orjson.JSONDecodeError`, which was added in that release (`cli.py` also uses `OPT_INDENT_2`). No code or behaviour change; this is a packaging fix only.

### 1.4.1
- **Dependency**: **Pytastic bumped to `>=0.4.1`**. Unlocks `Pytastic.patch()` (partial-payload validation), the `dot=True` option on `validate()`/`patch()` for DotDict-wrapped return values, and `Pytastic.use(other, prefer=...)` for merging registrations across instances.
- **Fix**: **`mount()` Now Shares Schemas and Pytastic Registrations**. Previously, `app.mount(api)` never copied `api.schema._schemas` or `api._pytastic` onto the parent, so any `api.schema.POST(...)` or custom `api.vx.*` registrations made before mount were silently dead weight at request time (the parent's baker only reads its own registries). `mount()` now: (1) calls `self._pytastic.use(router._pytastic)` to absorb the child's pytastic registrations; (2) copies `router.schema._schemas` entries onto the parent so they bake into validation hooks; (3) rebinds `router._pytastic` and `router.schema` to the parent's instances so any post-mount registrations on the child also land on the shared state.
- **Feature**: **`mount(prefer=...)` Conflict Resolution**. `mount()` accepts a new `prefer` argument to decide who wins on pytastic registration conflicts. Accepts `'parent'`/`'self'` (parent keeps its registration), `'child'`/`'incoming'` (mounted router overrides), a raw `Pytastic` instance (passed straight to `Pytastic.use(prefer=...)`), or `None` (default — raises on conflict so accidental overlaps are surfaced).
- **Feature**: **Opt-in Dot-Dict Access on `req.data`**. All `schema` methods (`POST`, `PUT`, `PATCH`, `DELETE`, `GET`) now accept `dot=True` to return validated payloads as pytastic DotDicts, enabling `req.data.name` alongside `req.data['name']`. Per-route and fully additive — defaults to plain dict, no breaking change. Example: `app.schema.PATCH("/workers/:id", expects=UpdateWorker, dot=True)`.
- **Feature**: **PATCH Uses Partial Validation**. `app.schema.PATCH(...)` now routes through `pytastic.patch()` instead of `pytastic.validate()`, so clients can submit only the fields they want to change without tripping required-field errors. Works with or without `dot=True`.

#### 1.4.0
- **Fix**: **BEFORE Hook Headers Preserved on Unhandled Exceptions**. When a route handler raises an unhandled exception, CORS and other headers set by BEFORE hooks are now preserved in the 500 response. Previously, exceptions escaped `handle()` and either re-raised to uvicorn (production) or created a new Response object (debug), discarding all BEFORE hook headers. The same response object is now returned with a 500 status and the exception attached as `_unhandled_error` for logging and Guardian Angel.
- **Fix**: **JSON Serialization Errors No Longer Wipe Headers**. When `orjson.dumps()` fails on a response body, the error handler no longer clears `response._headers`. Previously, all headers (including CORS) were wiped with `response._headers = []`.

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
