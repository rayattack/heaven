# Minute 9: Centralized Middleware & Snippets

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
        # res.abort stops the request cycle immediately
        res.abort('Unauthorized Access', status=HTTPStatus.UNAUTHORIZED)
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
        res.abort(f"Invalid Data: {str(e)}", status=400)

app.BEFORE('/api/v1/login', validate_json)

async def login(req: Request, res: Response, ctx: Context):
    payload = ctx.payload
    print(f"Logging in {payload['email']}")
    res.body = {"status": "ok"}

app.GET('/api/v1/login', login)
```

> [!TIP]
> Use `.BEFORE('*', handler)` to run a hook for every single request in your application (e.g., for logging or CORS).