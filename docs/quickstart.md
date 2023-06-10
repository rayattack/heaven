# Minute 1
We are assuming you have installed heaven via `pip install heaven`. If no, then go ahead and install it; If you have, then **the clock is ticking so** let's dive in.

----------------------

##### 1. Create a handler function

```python
import json
from http import HTTPStatus

from heaven import Request, Response, Context

async def get_one_customer(r: Request, w: Response, c: Context):
	id = r.params.get('id')
	w.status = HTTPStatus.CREATED
	w.body = json.dumps({"message": f"heaven is easy for customer {id}"})

```

As you can see above - your handler function can be async if you desire and must accept 3 arguments that will be injected by heaven. We'll get back to them in [Minute 3]()

-----------------------

##### 2. Connect your handler to the heaven application

```python
from heaven import Router

# create the application
router = Router()

# connect it to a route
router.GET('/v1/customers/:id', get_one_customer)
```

All HTTP methods i.e. `GET`, `POST` etc. are all supported

-----------------------

&nbsp;

# Minute 2
That was quick wasn't it? even less than a minute?

Well now we have an application, but it is no fun if we can't execute/run/interact with it.

-----------------------

##### 3. Run your heaven application

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

&nbsp;

# Minute 3 &amp; 4
A promise is a promise. So it's time to tell you about heaven's objects. **_Don't fret - there are only 4 of them._**


#### 1. Request
All handlers will receive this as their first argument i.e. **`...(r: Request, ..., ...)`** and all Request objects come with the following bag of goodies.

- **`r.app: Router`** -> An instance of the base heaven application

- **`r.body: dict`** -> The body sent along with the request

- **`r.cookies: dict`** -> All the cookies sent with request **_[keys in lowercase]_**

- **`r.headers: dict`** -> All the headers sent with request **_[keys in lowercase]_**

- **`r.method: str`** -> `GET`, `POST`, `DELETE`? What method type is the http request

- **`r.params: dict`** -> Querystring parameters and url masks `/customers/:param1` parsed into a dictionary

- **`r.querystring: str`** -> The part after the `?` i.e. example.com**?age=34** parsed in comma separated string form

- **`r.subdomain: str`** -> If request was made to a subdomain i.e. `www.example.org` or `api.example.org` then this holds the subdomain value e.g. `www` and `api`.

- **`r.url: str`** -> The url that matched to this handler as sent by the client

-----------------------

#### 2. Response
All handlers receive this as the second argument i.e. **`...(..., w: Response, ...)`** as Responses help with responding to Requests.

- **`w.abort(payload: any)`** -> If this is calledx then all `PRE` and `POST` [hooks]() will be aborted

- **`w.body: any`** -> This will be sent back as the body of the response

- **`w.headers: tuple[2] | list[2]`** -> How headers are set i.e. `w.headers = 'Set-Cookie', 'Token=12345; Max-Age=8700; Secure; HttpOnly'`

- **`w.status: int`** -> HTTP status code to be sent back with the response

-----------------------

#### 3. Context
All handlers receive this as the third argument i.e. **`...(..., ..., c: Context)`** to help with preserving state across a request lifecycle i.e. from start/reciept to finish/response.

- **`c.keep(alias: str, value: any)`** -> Save something that can be retrieved via [Python descriptor]() semantics. i.e. `c.alias` will return the kept value.

-----------------------

#### 4. Router
This is the last internal heaven object to grok. You can instantiate it with an optional configuration that is stored as the application's global state.
```py
router = Router({'secret_key': '...'})
# or
router = Router(function() -> dict)
```
-----------------------

- **`router.AFTER(url: str, handler: func, subdomain: str)`** -> Get a config value from the global store/state register

- **`router.BEFORE(url: str, handler: func, subdomain: str)`** -> Get a config value from the global store/state register

- **`router.CONFIG(url: str, handler: func, subdomain: str)`** -> Get a config value from the `final readonly` app config set at router instantiation.

- **`router.GET(url: str, handler: func, subdomain: str)`** -> Registers your custom handlers/functions to be invoked when a url match is made. `POST`, `PUT`, `PATCH`, `DELETE` etc.
all work in similar fashion. The `subdomain` optional argument limits the matching to a subdomain.

- **`router.HTTP(url: str, handler: func)`** -> Registers your custom handlers/functions to all HTTP methods i.e. GET, PUT, POST, PUT, PATCH instead of doing it individually.

- **`router.keep(key: str, value: any)`** -> Like. `c.keep()` but persisted across multiple request lifecycles.

- **`router.peek(key: str, value: any)`** -> Take a peek at your global dynamic application state without removing the kept value.

- **`router.unkeep(key: str, value: any)`** -> Remove and return the kept value from the global dynamic application state. 

-----------------------

&nbsp;

# Minute 5 : FAQs Anyone?
Whew... You made it here, we are super proud of you.

One last thing and you will be all set to create anything with a shiny powerful web framework. It's time to answer your questions.

1. What of authentication and authorization?

	Routerling is a microframwork so you have to roll your own which is [pretty simple to do with python decorators]().

2. 
