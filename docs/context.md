# The Context 🧠

The `Context` object is your request-scoped memory. It allows you to pass data between hooks, middlewares, and handlers without cluttering function signatures.

The handler signature:

```python
async def handler(req, res, ctx):
    ...
```

## Usage

### Storing Data
You can store data directly on the context using dot notation.

```python
app.BEFORE('/dashboard/*', auth_middleware)

async def auth_middleware(req, res, ctx):
    user = await db.get_user(req.headers['token'])
    ctx.user = user
```

### Retrieving Data
Once stored, data is available as a property on the `ctx` object.

```python
async def dashboard_handler(req, res, ctx):
    # Retrieve 'user' stored by auth_middleware
    print(f"Welcome back {ctx.user.name}")
```

!!! warning "Warning"
    You cannot overwrite reserved keys like `ctx.session`, `ctx.request`, or `ctx.app`. Use `ctx.keep('session', val)` only if you know exactly what you are doing.

## Typed Keys (New in 1.3.7)

When working on large applications, relying on string keys or dynamic attributes can lead to typing issues. Heaven now provides a `Key` generic for type-safe context storage.

```python
from heaven import Key, App

# Define typed keys
UserID = Key[int]("user_id")
IsAdmin = Key[bool]("is_admin")

async def middleware(req, res, ctx):
    # Type checkers know this expects an int
    ctx.keep(UserID, 42) 
    
    # This would raise a static type check error!
    # ctx.keep(UserID, "not an int")

async def handler(req, res, ctx):
    # Returns int | None (auto-inferred)
    uid = ctx.peek(UserID)
    
    # Returns bool | None
    admin = ctx.peek(IsAdmin)
```

This works for both `ctx.keep/peek` (request-scoped) and `app.keep/peek` (application-scoped).

## Why not modifies `req`?

Some frameworks attach data to the `Request` object. Heaven believes in separation of concerns.

- **Request**: What the client sent (Immutable-ish).
- **Context**: What the server figured out (Mutable).
- **Response**: What the server is sending (Your Envelope).

### Session Management
If you enable `app.sessions()`, the session data lives here.

```python
# Read
user_id = ctx.session.user_id

# Write
ctx.session.visited = True
```

---

**Next:** We've covered the basics. Now let's superpower your app with Schemas. On to **[Interceptors](hooks.md)**.