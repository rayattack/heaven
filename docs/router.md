`View Source Code: ` [`Open on GitHub`](https://github.com/rayattack/heaven/blob/main/heaven/router.py)

# Minute 5


### Object \#4: Router | Application | App
A heaven `App`, `Application`, or `Router` can be imported by any of it's aliases and is what you deploy.

-------------------------

```py
from heaven import App
from heaven import Router
from heaven import Application

yes = App == Router == Application
```

--------------------------

## Heaven is A Router

```py
router = Router()


handler = lambda req, res, ctx:...


# GET, POST, PUT, PATCH, OPTIONS, DELETE, TRACE, all supported
router.GET('/read', handler)
router.POST('/write', handler)


# register this handler for all http methods i.e. GET, POST, PUT, OPTIONS, etc...
router.HTTP('/all', handler)


# run this handler before all orders routes
router.BEFORE('/orders/*', handler)

# or even after
router.AFTER('/orders/*', handler)
```

#### Additional Router APIs

- **`router.AFTER(url: str, handler: func, subdomain: str)`** -> This is called a hook - a function that is hooked to run **after** all matching routes.
    ```py
    message = 'I will run after all /v1/* routes'
    router.AFTER('/v1/*', lambda req, res, ctx: print(message))

    # will run after
    router.GET('/v1/customers', ...)
    router.POST('/v1/leads', ...)

    # but not after
    router.GET('/v2/customers')
    ```

- **`router.BEFORE(url: str, handler: func, subdomain: str)`** -> Same as **after hook above** - but runs before all matching routes.

- **`router.GET(url: str, handler: func, subdomain: str)`** -> Registers your custom handlers/functions to be invoked when a request matches
    the provided url. **All other HTTP** methods `POST`, `PUT`, `PATCH`, `DELETE` etc. 
    work in similar fashion. The `subdomain` optional argument limits the matching to a subdomain.

- **`router.HTTP(url: str, handler: func)`** -> Registers your custom handlers/functions to all HTTP methods i.e. GET, PUT, POST, PUT, PATCH instead of doing it individually.
- **`router.schema`** -> A registry for attaching metadata (OpenAPI schemas) to routes. It supports `GET`, `POST`, `PUT`, `DELETE`, and `PATCH` methods.
    ```py
    from heaven import Schema

    class User(Schema):
        id: int
        name: str

    # Sidecar registration of metadata
    app.schema.POST('/users', expects=User, returns=User, summary="Create User")
    ```

    > [!TIP]
    > Heaven's `Schema` is a direct export of the high-performance `msgspec.Struct`. To learn more about advanced features like default values, tagging, and validation, visit the [msgspec documentation](https://jcristharif.com/msgspec/structs.html).

    #### Advanced Schema Options
    You can control how Heaven handles incoming and outgoing data using these optional flags in `.schema` methods:

    - **`protect: bool`**: When `True` (default), Heaven will automatically "protect" your response data by removing any fields not present in the `returns` schema. This is perfect for leak-proofing APIs.
    - **`partial: bool`**: When `True`, Heaven allows "subset matching." If your response is missing some fields from the schema, it will still pass (default: `False`).
    - **`strict: bool`**: When `True` (default), output validation failures (missing required fields) will result in a `500 Internal Server Error`. If `False`, it will only log a warning and return the data as-is.

    ```python
    # Example: Return only what's in User schema, even if DB returns more.
    # Allow missing fields (partial) and just warn on mismatch (strict=False).
    app.schema.GET('/users/:id', returns=User, protect=True, partial=True, strict=False)
    ```

    You can also set these globally when initializing your app:
    ```python
    app = App(protect_output=True, allow_partials=False, fail_on_output=True)
    ```

- **`router.DOCS(route: str, title: str = "API Reference", version: str = "0.0.1")`** -> Automatically generates a dynamic `openapi.json` and serves an interactive **Scalar** API reference at the provided route.
    ```py
    app.DOCS('/api/docs', title="My Insanely Fast API")
    ```

- **`router.earth`** -> The built-in testing utility. It provides a clean API for both integration and unit testing.

    #### Integration Testing
    Simulate full requests through the entire framework stack (Hooks, Matching, Handlers, Protection).
    ```py
    # Returns the actual (req, res, ctx) trio used during the lifecycle
    req, res, ctx = await app.earth.POST('/users', body={"name": "Ray"})

    assert res.status == 201
    assert res.json['name'] == "Ray"
    ```

    #### Unit Testing Handlers
    Use atomic factories to construct a "trio" for testing handlers in isolation.
    ```py
    from my_handlers import create_user

    req = app.earth.req(url='/users', body={"name": "Jane"})
    res = app.earth.res()
    ctx = app.earth.ctx()

    await create_user(req, res, ctx)
    assert res.status == 201
    ```

    #### Lifecycle & Session Tracking
    Use the `test()` context manager to run `STARTUP`/`SHUTDOWN` hooks and track cookies across requests.
    ```py
    async with app.earth.test() as earth:
        # Startup hooks (e.g., DB connections) have run here
        await earth.POST('/login', body={"user": "admin"}) # Sets a cookie
        req, res, ctx = await earth.GET('/dashboard')    # Cookie tracked automatically
        assert res.status == 200
    ```

    #### Subdomain Testing
    Heaven is built for subdomains. You can specify which subdomain to target in your tests.
    ```py
    # Defaults to 'www'
    req, res, ctx = await app.earth.GET('/api-info', subdomain='api')
    assert res.status == 200
    ```

    #### Middleware Bypass
    Sometimes you want to test a route but skip a heavy or blocking middleware (like a complex Auth check).
    ```py
    app.earth.bypass(heavy_middleware)
    
    async with app.earth.test() as earth:
        # heavy_middleware will be skipped for all requests in this block
        await earth.GET('/fast-route')
    ```

    #### File Uploads
    Testing multipart/form-data is easy with the `upload` helper.
    ```py
    files = {'image': b'binary_data_here'}
    req, res, ctx = await app.earth.upload('/save-avatar', files=files, data={'id': '123'})
    assert res.status == 200
    ```

    #### WebSocket Testing
    Simulate real-time interactions without a real server.
    ```py
    # 1. Connect
    ws = await app.earth.SOCKET('/chat').connect()
    
    # 2. Communicate
    await ws.send("Hello Heaven!")
    response = await ws.receive()
    
    # 3. Cleanup
    await ws.close()
    ```

    #### Mocking Infrastructure
    Heaven provides two powerful ways to "unplug" real services (like databases) during tests.

    **Strategy 1: Hook Swapping**
    If you use `app.ON(STARTUP, ...)` to connect to a database, you can swap it for a test version before running your tests.
    ```py
    async def use_test_db(app):
        # Connect to a local SQLite instead of Production PG
        app.keep('db', TestDB())

    async def test_my_app():
        app.earth.swap(connect_to_real_db, use_test_db)
        async with app.earth.test() as earth:
            # STARTUP now runs use_test_db instead
            await earth.GET('/data')
    ```

    **Strategy 2: Bucket Overwriting**
    Since Heaven handlers rely on "Buckets" via `app.peek`, you can simply overwrite the bucket inside your test block.
    ```py
    async def test_simple_mock():
        async with app.earth.test() as earth:
            # Overwrite the 'db' bucket with a mock
            app.keep('db', MockDB())
            
            await earth.GET('/data')
            # The handler calling app.peek('db') will get the mock!
    ```

## Heaven is a Global Config & Store

### Global Config
```py
router = Router({'secret_key': 'not so secret...'})
```
This will be available in all handlers via the `req.app.CONFIG

#### Additional Store/State APIs

- **`router.keep(key: str, value: any)`** -> Like. `c.keep()` but persisted across multiple request lifecycles.

- **`router.peek(key: str, value: any)`** -> Take a peek at your global dynamic application state without removing the kept value.

- **`router.unkeep(key: str, value: any)`** -> Remove and return the kept value from the global dynamic application state. 

-----------------------


##### Customizing Your Heaven Application

```py
# development
from aiomysql import connect as Connection
from redis import Redis
from heaven import App  # also available as Router, Application


app = App()


# adding a database connection?
async def database_middleware(router: Router):
    client = await Connection(host='localhost', port=3306, user='root', password='', db='mysql')
    router.keep('db', client)


# synchronous initialization also supported
def upredis(router: Router):
    redis = Redis('localhost')
    router.keep('redis', redis)


# now use it in your handlers
async def create_order(req: Request, res: Response, ctx: Context):
    db: Connection = req.app.peek('db')
    await db.execute('''INSERT ...''')


app.ON(STARTUP, updatabase)
app.ON(SHUTDOWN, downdatabase)
app.ONCE(upredis)


app.POST('/orders', create_order)
```

-----------------------

-----------------------

## Daemons: Native Background Tasks 👻

Daemons are one of Heaven's most powerful features. They are long-running background tasks that live for the entire lifecycle of your application.

!!! warning "The Blocking Rule"
    Heaven runs on a single-threaded event loop. If you write a background task that performs heavy computation or blocking I/O (like `time.sleep()`), it will freeze the entire server. 

    **Note**: As of version 0.6.2, Heaven automatically offloads synchronous daemons to a separate thread pool to prevent accidental freezes, but using `async` functions remains the gold standard for performance.

Unlike FastAPI or Flask, which often require external libraries like Celery or Dramatiq for background processing, Heaven has background workers built directly into the core.

### Why Daemons are powerful:
1. **Periodic Jobs**: Easily run a task every `X` seconds (like a heartbeat or cache warmer).
2. **Event Loops**: Listen to a message queue or a database stream in the background.
3. **Internal Tools**: Run health checks or cleanup scripts without affecting request latency.

### Creating a Daemon

A daemon is just a function that takes the `app` instance as its only argument.

```python
async def my_daemon(app):
    print("Doing background work...")
    
    # If you return a number, the daemon will sleep for that many 
    # seconds and then run again automatically.
    return 10 

app.daemons = my_daemon
```

If you return `None` or `False`, the daemon will run exactly once and then stop.

-----------------------

##### 2. Running your heaven application in production

```sh
# development
uvicorn application:router --reload

# production
gunicorn -w 4 -k uvicorn.workers.UvicornWorker application:router
```

Replace the number after `-w` with the number of processors you desire to run your app with.

!!! info "Slow Down Tiger"
    You might be asking - what about the applications port number etc? 😁

-----------------------