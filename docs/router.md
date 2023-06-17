# Minute 5: Router | Application | App
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

- **`router.AFTER(url: str, handler: func, subdomain: str)`** -> Get a config value from the global store/state register

- **`router.BEFORE(url: str, handler: func, subdomain: str)`** -> Get a config value from the global store/state register

- **`router.GET(url: str, handler: func, subdomain: str)`** -> Registers your custom handlers/functions to be invoked when a url match is made. `POST`, `PUT`, `PATCH`, `DELETE` etc.
all work in similar fashion. The `subdomain` optional argument limits the matching to a subdomain.

- **`router.HTTP(url: str, handler: func)`** -> Registers your custom handlers/functions to all HTTP methods i.e. GET, PUT, POST, PUT, PATCH instead of doing it individually.


## Heaven is a Store

```py
```

#### Additional Store/State APIs

- **`router.keep(key: str, value: any)`** -> Like. `c.keep()` but persisted across multiple request lifecycles.

- **`router.peek(key: str, value: any)`** -> Take a peek at your global dynamic application state without removing the kept value.

- **`router.unkeep(key: str, value: any)`** -> Remove and return the kept value from the global dynamic application state. 

-----------------------


# Minute 5
That was quick wasn't it? even less than a minute?

Well now we have an application, but how can you customize your heaven application or even run it in production.


-----------------------

##### 1. Customizing Your Heaven Application

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