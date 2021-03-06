**********
# Routerling

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

def get_customer_orders(r: HttpRequest, w: ReponseWriter, s: State):
    w.headers = "go-go-gadget", ""
    w.body = '{customer: {customer_id}, orders: []}'.format(r.params.get('id'))

def change_headers(r: HttpRequest, w: ResponseWriter, s: State):
    w.headers = "go-go-gadget", "i was changed after..."

def create_customer(r: HttpRequest, w: ResponseWriter, s: State):
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
    body: str = r.body
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

> Documentation coming soon


&nbsp;

&nbsp;

# Socket Connections

> Documentation coming soon
