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
    from msgspec import Struct

    class User(Struct):
        id: int
        name: str

    # Sidecar registration of metadata
    app.schema.POST('/users', expects=User, returns=User, summary="Create User")
    ```

- **`router.DOCS(route: str, title: str = "API Reference", version: str = "0.0.1")`** -> Automatically generates a dynamic `openapi.json` and serves an interactive **Scalar** API reference at the provided route.
    ```py
    app.DOCS('/api/docs', title="My Insanely Fast API")
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