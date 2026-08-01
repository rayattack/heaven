# Min 17-18 — Hooks 🪝

Heaven has no middleware stack. Instead of wrapping your app in layers of opaque callables, you register **hooks** that run `BEFORE` or `AFTER` a request.

A hook is just a handler. Same signature, same objects, no special base class:

```python
async def check_auth(req, res, ctx):
    ...
```

## The request lifecycle

```mermaid
flowchart TD
    A(["Request"]) --> B["Match route"]
    B -->|"no match"| Z["404"]
    B --> C["BEFORE hooks"]
    C -->|"res.abort()"| Y["Response sent immediately<br/><b>AFTER hooks skipped</b>"]
    C --> D["Handler"]
    D --> E["AFTER hooks"]
    E --> F["Response sent"]
    F --> G["res.defer() callbacks"]
```

Everything you'd reach for middleware to do — auth, logging, rate limiting, headers, timing — is a `BEFORE` or an `AFTER` hook.

## Registering hooks

Hooks are matched by path pattern, with `*` as a wildcard suffix.

```python
app.BEFORE('/*', log_request)              # every request
app.BEFORE('/api/*', rate_limiter)         # everything under /api
app.AFTER('/users/:id', log_access)        # one specific route
```

### Scoping to methods

Pass `methods=` to run a hook only for certain verbs:

```python
app.BEFORE('/orders', validate_payload, methods=['POST', 'PUT'])
```

!!! danger "Do not reuse one hook function with mixed method scopes"
    Method scoping is stored **on the function object**, not on the registration. Registering the same function twice — once scoped, once not — makes the scope leak into both, and the unscoped registration silently stops running.

    ```python
    app.BEFORE('/x', shared, methods=['POST'])
    app.BEFORE('/y', shared)      # ⚠️ now also POST-only; never runs on GET /y
    ```

    If you need one piece of logic in two places with different scopes, wrap it in two thin functions.

## Execution order

Hooks run in the order they were registered — **within the same specificity**. Across specificities, Heaven runs **exact-match hooks first, then wildcard hooks**.

```python
app.BEFORE('/*', global_auth)          # registered first
app.BEFORE('/dashboard', page_hook)    # registered second
```

Actual order for `GET /dashboard`:

```
page_hook  →  global_auth  →  handler  →  (AFTER: exact, then wildcard)
```

!!! danger "Your `/*` guard runs *last*, not first"
    This is the single most surprising thing in Heaven, and it matters most for the case you'd most want it: **authentication registered on `/*` runs after route-specific hooks**, so a route hook can execute before the auth check that was supposed to protect it.

    Until this is addressed, register security-critical guards on the **exact prefix they protect** rather than on `/*`:

    ```python
    app.BEFORE('/admin/*', require_admin)   # ✅ scoped to what it guards
    app.BEFORE('/*', require_admin)         # ⚠️ runs after more specific hooks
    ```

Each hook runs at most once per request even if several patterns match it.

## What a hook can do

```python
async def auth(req, res, ctx):
    user = await lookup(req.headers.get('authorization'))

    if not user:
        res.status = 401
        res.abort('Unauthorized')       # stop here — handler never runs

    ctx.user = user                     # hand data to the handler
```

- **Read the request** — headers, cookies, body, params.
- **Write to the context** — this is how hooks talk to handlers.
- **Set response headers or status** — an `AFTER` hook can decorate any response.
- **Abort** — `res.abort(body)` ends the request immediately.

!!! warning "`abort()` skips every AFTER hook"
    That includes Heaven's own session-saving hook. If a `BEFORE` hook aborts — or a schema validation fails with a 422 — session writes made during that request are silently discarded.

## A worked example: request timing

```python
import time

async def start_timer(req, res, ctx):
    ctx.started = time.perf_counter()

async def record_timing(req, res, ctx):
    elapsed = (time.perf_counter() - ctx.started) * 1000
    res.headers = 'X-Response-Time', f'{elapsed:.1f}ms'

app.BEFORE('/*', start_timer)
app.AFTER('/*', record_timing)
```

This is the pattern for nearly all middleware in Heaven: stash something in `ctx` on the way in, use it on the way out.

## Hooks and mounting

When you mount a child app onto a parent, hooks nest the way you'd want:

- **`BEFORE`**: parent hooks, then child hooks — broad guard before specific logic.
- **`AFTER`**: child hooks, then parent hooks — specific cleanup unwinds first.

## CORS is just a hook

```python
app.cors(origin=['https://myapp.com'], credentials=True)
```

Under the hood this registers a `BEFORE('/*')` hook that sets the `Access-Control-*` headers and a catch-all `OPTIONS` route that short-circuits preflights. Nothing you couldn't write yourself in fifteen lines — see [The Router](router.md#cors) for the options.

---

**Next:** Contracts, validation, and typed bodies → **[Min 19-20 — Schemas & Validation](schema.md)**
