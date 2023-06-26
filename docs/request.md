# Minute 2
A promise is a promise. So it's time to tell you about heaven's objects. **_Don't fret - there are only 4 of them._**


### Object \#1: Request
All handlers will receive this as their first argument i.e. **`...(req: Request, ..., ...)`** -
and all Request objects come with the following helper properties (bag of goodies).

- **`req.app: Router`** -> An instance of the base heaven application

- **`req.body: bytes`** -> The body sent along with the request

- **`req.cookies: dict`** -> All the cookies sent with request **_[keys in lowercase]_**

- **`req.form: Form`** -> If **content-type** of `req` is `multipart/form-data`, this will return a form object - a light
    wrapper on a dict.
    ```py
    def create_lead(req, res, ctx):
        form = req.form
        print(form.name)
        print(form.password)
    ```

- **`req.headers: dict`** -> All the headers sent with request **_[keys in lowercase]_** i..e `req.headers.get('content-type')`

- **`req.method: str`** -> `GET`, `POST`, `DELETE`? What method type is the http request

- **`req.mounted: app`** -> [The mounted router](mount.md) if this request handler is from a mounted router.
    ```py
    from router import Router, App

    router_1 = Router()
    router_1.GET('/', lambda req, res, ctx:...)

    app = App()
    app.mount(router) # all routes defined on router_1 will be mounted to app
    ```
    Useful if you have different configurations on child routers and want to access them separately.

- **`req.params: dict`** -> Querystring parameters and url masks `/customers/:param1` parsed into a dictionary

- **`req.querystring: str`** -> The part after the `?` i.e. `example.com`**?age=34** parsed in comma separated string form

- **`req.scheme: dict`** -> `http` or `https` i.e. what protocol is current request using.

- **`req.subdomain: str`** -> If request was made to a subdomain i.e. **www**`.example.org` or **api**`.example.org`
    then this holds the subdomain value e.g. `www` and `api`.

- **`req.url: str`** -> The url that matched to this handler as sent by the client

-----------------------

&nbsp;

[Next: Requests to Heaven](request.md)
