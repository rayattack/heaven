#### Alphabetical List of All Heaven APIs

- **`constants.DEFAULT`** -> A `str` constant helpful to preven you from typing `'www'` everywhere in your code.

- **`constants.WILDCARD`** -> A `str` constant helpful to prevent you from typing `'*'` everywhere in your code.

- **`context.keep(key: str, value: any)`** -> This is how values are kept/stored in the context API for use across http requests.
    _see [decorator code snippet](examples.md#decorator-functions) for example on its usage_

- **`form.Form`** -> Tiny wrapper around a dict returned from `req.FORM` when **content-type** of request is of type `multitype/form-data` or
    `application/x-www-form-urlencoded`
    ```py
    from heaven.form import Form

    HEADERS = ['multitype/form-data', 'application/x-www-form-urlencoded']

    async def example(req, res, ctx):
        if(req.headers.get('content-type') in HEADERS):
            isinstance(req.form, Form)  # --> True
            print(form.email)
            print(form.password)
        else:
            assert req.form is None  # --> True
    ```

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

- **`router.CONNECT(url: str, handler: func, subdomain: str)`** -> Registers your custom handlers/functions to be invoked when a `CONNECT` http
    request to the provided `url` is received.

- **`router.DELETE(url: str, handler: func, subdomain: str)`** -> Registers your custom handlers/functions to be invoked when a `DELETE` http
    request to the provided `url` is received.

- **`router.GET(url: str, handler: func, subdomain: str)`** -> Registers your custom handlers/functions to be invoked when a `GET` http
    request to the provided `url` is received.

- **`router.HEAD(url: str, handler: func, subdomain: str)`** -> Registers your custom handlers/functions to be invoked when a `HEAD` http
    request to the provided `url` is received.

- **`router.HTTP(url: str, handler: func, subdomain: str)`** -> Registers the same `handler` `func: Callable[[Request, Response, Context], None]`
     to be called for `ALL` http request methods i.e. GET, PUT, POST, PUT, PATCH etc. instead of doing it individually.
    ```py
    # this is one line
    router.HTTP('/', lambda req, res, ctx: res.renders('index.html'))

    # but is the same as this
    router.CONNECT('/', lambda req, res, ctx: res.renders('index.html'))
    router.DELETE('/', lambda req, res, ctx: res.renders('index.html'))
    router.GET('/', lambda req, res, ctx: res.renders('index.html'))
    router.HEAD('/', lambda req, res, ctx: res.renders('index.html'))
    router.OPTIONS('/', lambda req, res, ctx: res.renders('index.html'))
    router.PATCH('/', lambda req, res, ctx: res.renders('index.html'))
    router.POST('/', lambda req, res, ctx: res.renders('index.html'))
    router.PUT('/', lambda req, res, ctx: res.renders('index.html'))
    router.TRACE('/', lambda req, res, ctx: res.renders('index.html'))
    ```

- **`router.OPTIONS(url: str, handler: func, subdomain: str)`** -> Registers your custom handlers/functions to be invoked when a `OPTIONS` http
    request to the provided `url` is received.

- **`router.PATCH(url: str, handler: func, subdomain: str)`** -> Registers your custom handlers/functions to be invoked when a `PATCH` http
    request to the provided `url` is received.

- **`router.POST(url: str, handler: func, subdomain: str)`** -> Registers your custom handlers/functions to be invoked when a `POST` http
    request to the provided `url` is received.

- **`router.PUT(url: str, handler: func, subdomain: str)`** -> Registers your custom handlers/functions to be invoked when a `PUT` http
    request to the provided `url` is received.

- **`router.TRACE(url: str, handler: func, subdomain: str)`** -> Registers your custom handlers/functions to be invoked when a `TRACE` http
    request to the provided `url` is received.
