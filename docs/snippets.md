# Middleware Snippets

Two short patterns for `.BEFORE` hooks. For the full treatment see [Hooks](hooks.md), and for production-ready versions see [Recipes](examples.md).

Heaven is extremely unopinionated, but it provides powerful tools for centralized control. This section shows how to use `.BEFORE` hooks for common tasks like Authentication and Data Validation.

## Centralized Authentication

Instead of littering your handlers with decorators, use `.BEFORE` to protect entire route trees at once.

```python
from http import HTTPStatus
from heaven import App, Request, Response, Context

app = App()

# 1. Define your protection logic
async def protect(req: Request, res: Response, ctx: Context):
    token = req.headers.get('authorization')

    # Use your preferred JWT or other validation scheme here
    if not token or token != "secret-token":
        res.status = HTTPStatus.UNAUTHORIZED
        res.abort('Unauthorized Access')
        return

    # Keep the user in context for the actual handler
    ctx.keep('user', {"id": 1, "name": "Raymond"})

# 2. Register it globally or for specific route patterns
app.BEFORE('/api/v1/*', protect)

# 3. Your handler stays clean and focused
async def get_secure_data(req: Request, res: Response, ctx: Context):
    user = ctx.user # Already populated by the hook
    res.body = {"data": "Top Secret", "for": user['name']}

app.GET('/api/v1/data', get_secure_data)
```

## Centralized Data Validation

You can also use `.BEFORE` to validate incoming data before it ever reaches your handler.

```python
import json
from heaven import App, Request, Response, Context

app = App()

async def validate_json(req: Request, res: Response, ctx: Context):
    try:
        data = json.loads(req.body)
        if "email" not in data:
            raise ValueError("Email is required")
        ctx.keep('payload', data)
    except Exception as e:
        res.status = 400
        res.abort(f"Invalid Data: {str(e)}")

app.BEFORE('/api/v1/login', validate_json)

async def login(req: Request, res: Response, ctx: Context):
    payload = ctx.payload
    print(f"Logging in {payload['email']}")
    res.body = {"status": "ok"}

app.GET('/api/v1/login', login)
```

!!! tip "Matching every request"
    Use `.BEFORE('/*', handler)` to run a hook for every request in your application, for logging, timing, or headers.

    The leading slash is required: `.BEFORE('*', handler)` raises `UrlError`. `/*` hooks run **before** more specific hooks, so a global guard precedes the route hooks it protects. See [execution order](hooks.md#execution-order).