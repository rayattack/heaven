# Minute 3: The Router 🛣️

The Router is the nervous system of your Heaven application. It decides where requests go, what runs before them, and what runs after.

## The Basic Contract

```python
from heaven import App

app = App() # An Alias for Router()

app.GET ('/users', get_users)
app.POST('/users', create_user)
app.PUT ('/users/:id', update_user)
app.DELETE('/users/:id', delete_user)
```

## The String Paradigm (Lazy Loading)

Heaven supports a "String Paradigm" that allows you to pass the **import path** of your handler instead of the function itself.

**This works everywhere.** Routes, Hooks, Lifecycle events, and Daemons.

#### 1. Routes

```python
# No need to import the function!
app.GET('/users', 'controllers.user.get_all')
app.POST('/users', 'controllers.user.create')
app.PUT ('/users/:id', update_user)
app.DELETE('/users/:id', delete_user)
```

#### 2. Hooks (Middleware)
```python
# Instead of: from middleware.auth import check_token
app.BEFORE('/dashboard/*', 'middleware.auth.check_token')
```

#### 3. Lifecycle
```python
# Instead of: from db import connect
app.ON('startup', 'db.connect')
```

### Why use strings?
1.  **Speed**: Modules are imported only when the application starts or when routes are hit.
2.  **Cleanliness**: No more 50-line import blocks at the top of your file.
3.  **Decoupling**: Solves circular import headaches instantly.

## Subdomains

Heaven handles subdomains natively. No "Blueprint" confusion.

```python
# Matches: https://api.mysite.com/users
app.GET('/users', handler, subdomain='api')

# Matches: https://admin.mysite.com/dashboard
app.GET('/dashboard', handler, subdomain='admin')
```

## Lifecycle Hooks: `ON` and `ONCE`

You have full control over the lifespan of your application.

### `ONCE(func)` or `ON(STARTUP, func)`
Run code when the server starts. Perfect for database connections.

```python
async def connect_db(app):
    db = await Database.connect()
    app.keep('db', db) # Persist it globally

app.ONCE(connect_db)
```

### `ON(SHUTDOWN, func)`
Clean up when the server stops.

```python
async def cleanup(app):
    db = app.peek('db')
    await db.close()

app.ON('shutdown', cleanup)
```

## Middleware: Hooks

Heaven doesn't use the confusing "middleware stack" pattern. instead, it uses explicit `BEFORE` and `AFTER` hooks.

### `BEFORE`
Runs before a request hits the handler. If you abort here, the handler never runs.

```python
async def check_auth(req, res, ctx):
    if not req.headers.get('Authorization'):
        res.abort('Unauthorized', status=401)

# Protects /dashboard and everything under it
app.BEFORE('/dashboard/*', check_auth)
```

### `AFTER`
Runs after the handler returns. Good for logging or modifying headers.

```python
async def add_server_header(req, res, ctx):
    res.headers = 'Server', 'Heaven/0.6'

app.AFTER('/*', add_server_header)
```

## Core Features: CORS & Sessions 🛡️

Heaven comes with built-in support for CORS and secure sessions.

### `app.cors()`
Enable Cross-Origin Resource Sharing with a single line.

```python
app.cors(origins='https://myapp.com', methods=['GET', 'POST'])
```

### `app.sessions()`
Enable signed, secure cookie-sessions.

```python
app.sessions(secret_key='keep-it-secret')

# In your handler:
# ctx.session.user_id = 123
```

## Daemons: Background Tasks 👻

Heaven has a built-in process manager for background tasks. No Celery required.

> [!WARNING]
> Heaven is single-threaded. **Never** block the main loop with `time.sleep()`.

### creating a Daemon
A daemon is a function that receives the `app` instance. If it returns a number `N`, it sleeps for `N` seconds and runs again.

```python
async def heartbeat(app):
    print("Lub-dub...")
    # Sleep 5 seconds, then repeat
    return 5

app.daemons = heartbeat
```

## Mounting Applications

You can mount entire other Heaven apps onto your main app. This is how you build modular monoliths.

```python
from heaven import App
from my_blog import blog_app
from my_store import store_app

main = App()

# Mounts blog_app at /blog
main.mount(blog_app) 

# Note: Mounting merges routes.
# If blog_app had a route '/posts', it is now accessible on main at '/posts'
# Wait, let's clarify alignment with minute 8.
```

> [!TIP]
> Use `mount` to split your code into multiple files/modules, then simply combine them in `main.py`.

---

**Next:** Now that we know how to route the request, let's learn how to read it. On to **[Minute 4: The Request](request.md)**.