# Interceptors (Hooks & Middlewares)

Heaven uses a centralized `interceptors` system to handle middleware. Instead of "wrapping" applications in layers of opaque middleware, you register *interceptors* i.e. **`hooks`**
that run **`.BEFORE`** or **`.AFTER`** a request.


## The Hook Lifecycle

1.  **Request arrives**.
2.  **Match Route**: The router finds the handler for the URL.
3.  **Run BEFORE Hooks**: Any hooks matching the URL are run.
4.  **Run Handler**: The actual route handler is executed.
5.  **Run AFTER Hooks**: Any hooks matching the URL are run.
6.  **Response sent**.

## Registering Hooks

!!! note "Note"
    Hooks are run in the order they are registered.

Hooks are registered with a glob-like URL pattern.

```python
# Run on EVERY request
app.BEFORE('/*', global_auth_check)  # run me 1st

# Run only on /api routes
app.BEFORE('/api/*', rate_limiter)  # run me 2nd

# Run on a specific route
app.AFTER('/users/:id', log_access)  # run me 3rd
```

### Execution Order & Mounting

1. **FIFO**: Hooks are executed in the exact order they are registered.
2. **Mounting**: When you mount a sub-application (`child`) onto a `parent` app, the order is preserved nicely:
    *   **BEFORE Hooks**: Parent hooks run **first**, then Child hooks. (Guard Pattern: Global Auth -> Specific Logic).
    *   **AFTER Hooks**: Child hooks run **first**, then Parent hooks. (Unwinding: Specific Cleanup -> Global Cleanup).

### The Hook Signature

Hooks share the exact same signature as route handlers.

```python
async def my_hook(req, res, ctx):
    # You can modify the request
    req.headers['x-checked'] = 'true'
    
    # You can modify the context
    ctx.user = await get_user(req)
    
    # You can ABORT the request (shortcuts the pipeline)
    if not ctx.user:
        res.status = 401
        res.abort("Unauthorized")
```

## CORS (Cross-Origin Resource Sharing)

CORS is a common requirement, so Heaven includes a dedicated helper that registers the necessary hooks for you.

### Simple
```python
# Allow everything (wildcard)
app.cors() 
```

### configured
```python
app.cors(
    origin='https://myapp.com',
    methods=['GET', 'POST'],
    headers=['Authorization', 'Content-Type'],
    max_age=3600 # or maxAge, MAX_AGE etc.
)
```

!!! note "Note"
    `app.cors` is smart enough to handle different casing styles for arguments (e.g. `max_age`, `maxAge`, `MAX_AGE` all work).

Note that `app.cors()` is just a wrapper that registers a `.BEFORE('/*')` hook that handles the `OPTIONS` method and sets the correct `Access-Control-*` headers.


**Next:** You know how to intercept, how about API Docs? On to **[Schemas](schema.md)**.