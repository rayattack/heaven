`View Source Code: ` [`Open on GitHub`](https://github.com/rayattack/heaven/blob/main/heaven/request.py)

# Minute 2
A promise is a promise. So it's time to tell you about heaven's objects. **_Don't fret - there are only 4 of them._**

### Object \#1: Request
All handlers will receive this as their first argument i.e. **`...(req: Request, ..., ...)`** -
and all Request objects come with the following helper properties (bag of goodies).

- **`req.app: Router`** -> An instance of the base heaven application
    ```py 
    from heaven import App

    app = App()

    # For instance if this app could talk it might tell you:
    # Hello my name is `your-app` - I am a Python web application
    # I spend my time serving web requests and 
    # when I am free - I spend my time dreaming of becoming a chess engine
    app_id = id(app)


    async def handler(req, res, ctx):
        # Hello again in all your handler functions
        # mounted on `app` - Your friendly neigborhood
        # `your-app` is present as well
        assert id(req.app) == app_id
    ```

- **`req.body: bytes`** -> The body sent along with the request
    ```py 
    ...
    from ujson import loads


    # for instance to process a post json request
    def handler(req: Request, res: Response, ctx: Context):
        body = loads(req.body)
    ...
    ```

- **`req.cookies: dict`** -> All the cookies sent with request **_[case sensitive - case preserved]_**
    ```py 
    ...

    def handler(req, res, ctx):
        # cookies are case sensitive
        token = req.cookies.get('Authorization')
        different_token = req.cookies.get('authorization')  
    ...
    ```

- **`req.form: Form`** -> If **content-type** of `req` is `multipart/form-data`, this will return a form object - a light
    wrapper on a dict.
    ```py
    ...

    def create_lead(req, res, ctx):
        form = req.form
        print(form.name)
        print(form.password)
    ...
    ```

- **`req.headers: dict`** -> All the headers sent with request **_[keys in lowercase]_** i..e `req.headers.get('content-type')`
    ```py 
    ...

    def handler(req: Request, res: Response, ctx: Context):
        # if a browser sends you a request with Content-Type application/json
        # then this will assert True
        assert req.headers.get('content-type') == 'application/json'
    ...
    ```

- **`req.method: str`** -> `GET`, `POST`, `DELETE`? What method type is the http request

- **`req.mounted: app`** -> The mounted router if this request handler is from a [mounted router](mount.md).
    ```py
    from router import Router, App

    router_1 = Router()
    router_1.GET('/', lambda req, res, ctx:...)

    app = App()
    app.mount(router_1) # all routes defined on router_1 will be mounted to app
    ...
    ```

    !!!Info
        Mounted `apps` or `routers` can be useful if you have different configurations
        on child routers and want to access them separately. e.g. **different routers can use
        different database connections** i.e. mongodb and postgres

- **`req.params: dict`** -> URL params i.e. `/customers/:param1` defined in as your part of your route(s) parsed into a
    dictionary  
    ```py
    # for the following routes
    app.GET('/customers/:id:int/messages/:message_id')

    def get_customer_messag_by_id(req: Request, res: Response, ctx: Context):
        '''when a user visits /customers/1/messages/33'''
        print(req.params)  # -> {'id': 1, 'message_id': '33'}
    ```

    !!!Note "From v0.3.11"
        In case you missed it - you can coerce url parameters into the following python types

        - `/v1/customers/:param:int` -> `int`
        - `/products/:id:str` -> `str` - this is the default so the `:str` can be omitted


- **`req.queries: dict`** -> Query string key value pairs i.e. `?limit=45&asc=name` parsed into a dictionary
    
    !!!Note "From v0.3.11"

        You can also coerce query parameters if present in the request url to the following python types

        - `?query1:datetime` -> `datetime.datetime`
        - `?query5:date` -> `datetime.date`
        - `?query2:int` -> `int`
        - `?query3:str` -> `str`
        - `?query4:float` -> `float`
        - `?query5:uuid` -> `uuid.UUID`

    To do this provide a suffix in your URL `route` declaration, and **don't worry - your URL will work
    the same as when it is not there**. The only difference will be that if the users of your app do provide
    query values then **Heaven** will attempt to parse them into the correct python data types.
    ```py
    ...

    # for instance for the following route
    app.GET('/customers/:id?limit:int&paginate:int&page:str')

    # when a user visits /customers/1?limit=44&page=3&pagination=100
    def get_customer_messag_by_id(req: Request, res: Response, ctx: Context):
        print(req.queries)  # -> {'limit': 44, 'pagination': 100, 'page': '3'}

    ...
    ```



- **`req.querystring: str`** -> The part after the `?` i.e. `example.com`**?age=34** parsed as a string
    without further processing or key value extraction performed.

- **`req.scheme: dict`** -> `http` or `https` i.e. what protocol was sent to your server on the current request using.

- **`req.subdomain: str`** -> If request was made to a subdomain i.e. **www**`.example.org` or **api**`.example.org`
    then this holds the subdomain value e.g. `www` and `api`.

- **`req.url: str`** -> The url that matched to this handler as sent by the client
    ```py 
    ...

    def handler(req: Request, res: Response, ctx: Context):
        # if handler is attached to app at app.GET('/v1/users/:id', ...)
        # if a visitor types /v1/users/3 into their browser
        # to visit your app then the following will be true
        assert req.url ==  '/v1/users/3'
    ...
    ```

-----------------------

&nbsp;

[Next: Response from Heaven](response.md)
