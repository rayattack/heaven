# Minute 6: The Context 🧠

The `Context` object is your request-scoped memory. It allows you to pass data between hooks, middlewares, and handlers without cluttering function signatures.

The handler signature:

```python
async def handler(req, res, ctx):
    ...
```

## Usage

### Storing Data
Use `ctx.keep(key, value)` to store data.

```python
app.BEFORE('/dashboard/*', auth_middleware)

async def auth_middleware(req, res, ctx):
    user = await db.get_user(req.headers['token'])
    ctx.keep('user', user)
```

### Retrieving Data
Once stored, data is available as a property on the `ctx` object.

```python
async def dashboard_handler(req, res, ctx):
    # Retrieve 'user' stored by auth_middleware
    print(f"Welcome back {ctx.user.name}")
```

## Why not modifies `req`?

Some frameworks attach data to the `Request` object. Heaven believes in separation of concerns.
- **Request**: What the client sent (Immutable-ish).
- **Context**: What the server figured out (Mutable).

---

**Next:** We've covered the basics. Now let's superpower your app with Schemas. On to **[Minute 7: Schema & Docs](schema.md)**.