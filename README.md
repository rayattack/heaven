# Routerling

<img src="https://img.shields.io/badge/coverage-92%25-green" />

A new born baby router on it's way to being a web development platform. Routerling is a router
multiplexer built with 1 goal in mind.

- Make it stupid simple to build high performance web applications


## How?
Following the unix philosophy of be the master of one thing and one thing only - Routerling has only **ONE** API you need to learn - `Router`. The API is also deliberately made
consistent across the 3 different supported languages [Golang, Python, Typescript/JavaScript].
[See Similarities](#similarities)

&nbsp;

## Python

```py
from routerling import Context, HttpRequest, ResponseWriter, Router
from logging import log

def get_customer_orders(r: HttpRequest, w: ReponseWriter, c: Context):
    w.headers = "go-go-gadget", ""
    w.body = '{customer: {customer_id}, orders: []}'.format(r.params.get('id'))

def change_headers(r: HttpRequest, w: ResponseWriter, c: Context):
    w.headers = "go-go-gadget", "i was included after..."

def create_customer(r: HttpRequest, w: ResponseWriter, c: Context):
    print(r.body)
    w.status = 201
    w.body = '{id: 13}'


# register functions to routes
router.BEFORE('/*', lambda req, res, state: print('will run before all routes are handled'))
router.AFTER('/v1/customers/*', change_headers)
router.GET('/v1/customers/:id/orders', get_customer_orders)
router.GET('/v1/customers/:id', lambda req, res, state: log(2, state.abcxyz_variable))
router.POST('/v1/customers', create_customer)
```

### Serve your application
```sh
uvicorn app:router
```


&nbsp;


## Request Object

- **request.body**
    > Body/payload of request if it exists. You can use any `XML, JSON, CSV etc.` library you prefer
    > to parse `r.body` as you like.
    ```py
    # r.body: str
    body: str = r.body
    ```

- **request.headers** `header = r.headers.get('header-name')`
    > All headers sent with the request.
    ```py
    # r.headers: dict
    header = r.headers.get('content-type')
    ```

- **request.params** `param = r.params.get('param-name')`
    > Dictionary containing parts of the url that matched your route parameters i.e. `/customers/:id/orders` will
    > return `{'id': 45}` for url `/customers/45/orders`.
    ```py
    identifier = r.params.get('id')
    ```

&nbsp;

## Response Object

- **response.abort**
    > Signals to routerling that you want to abort a request and ignore all `GET`, `POST`, `PUT etc.` handlers including all
    > `AFTER` or `BEFORE` hooks from executing. The payload given to abort is used as the response body.
    > Only calling `w.abort() will not end function execution.` You have to explicitly return from the request handler after using w.abort().

    ```py
    w.abort('This is the body/payload i want to abort with')
    return

    # or

    return w.abort('This is the body/payload i want to abort with')  #abort registers then returns None
    ```

- **response.body**
    > Used to set payload/body to be sent back to the client. Returning data from a handler function does not do
    > anything and is not used by routerling. `To send something back to the client use w.body`.

    ```py
    w.body = b'my body'
    ```

- **response.headers**
    > Used to set headers to be sent back to the client.

    ```py
    w.headers = "Content-Type", "application/json"
    w.headers = ["Authorization", "Bearer myToken"]
    ```

&nbsp;

## Context Object

- **context.keep**
    > Used to store values across different request handlers for any given request lifecylce i.e. from the time
    > a client browser hits your server (request start) to  the time a response is sent back to client (request end).
    >
    > &nbsp;
    >
    > **Sample Use Case**
    >
    > Imagine you want to use the amazing [**jsonschema**](https://pypi.org/project/jsonschema/) library to
    > validate json request payloads received on every **POST**, **PATCH**, or **PUT** request from your users.
    > One way to achieve this is to decorate your request handlers and abort the request if the json payload does not
    > match your schema validation constraints.
    > 
    > _The code snippet below shows a sample implementation for such a use case for reference_.


    ```py
    from http import HttpStatus as status
    from json import dumps, loads  # consider using ujson in production apps

    from jsonschema import validate, draft7_format_checker
    from jsonschema.exceptions import ValidationError

    def expects(schema):
        def proxy(func):
            @wraps(func)
            async def delegate(r: HttpRequest, w: ResponseWriter, c: Context):
                body = loads(r.body)
                try: validate(instance=body, schema=schema, format_checker=draft7_format_checker)
                except ValidationError as exc:
                    w.status = status.NOT_ACCEPTABLE
                    w.headers = 'content-type', 'application/json'
                    return w.abort(dumps({'message': exc.message}))

                # Here we call Context.keep('key', value) to store values across handlers for the request lifecycle
                # -------------------------------------------------------------------------------------------------
                for k,v in body.items(): c.keep(k, v)
                return await func(r, w, c)
            return delegate
        return proxy


    @expects({
        'type': 'object',
        'properties': {
            'username': {'type': 'string'}
            'password': {'type': 'string', 'minLength': 8}
        }
    })
    async def handler(r: HttpRequest, w: ResponseWriter, c: Context):
        print(c.username, " you can do this because the @expects :func: calls c.keep('username', value)")
        print(c.password, " ^^^ same for this")
        w.body = dumps({'username': username, 'password': password})
    ```

- **context._application** 
    > Retrieves the root _Routerling_ **app** instance (root router instance), after all you are an
    > adult when it comes to coding ;-)
    >
    > Newly introduced in routerling **version 0.2.3**

&nbsp;

&nbsp;

# Socket Connections

> Implementation &amp; Documentation coming soon
