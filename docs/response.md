`heaven.response.Response: ` [`Open on GitHub`](https://github.com/rayattack/heaven/blob/main/heaven/response.py)

# Minute 3


### Object \#2. Response
All handlers receive this as the second argument i.e. **`...(..., res: Response, ...)`** with
the following `properties` & `methods` to help with responding to http requests.

-----------------------

- **`res.body: any = 'hello'`** -> Sets the body that will be sent back with the response object.

- **`res.defer: Callable = lambda router: isinstance(router, Router)`** -> Registers a function to be called after the
        response is sent to the client. Callable must accept a single parameter of `type: Router | Application`
        ```py
        def send_sms_after_request(router: Router):
                twilio = router.peek('twilio')
                twilio.messages.create(to='+123456', from='+123456', body='Hi!')


        async def create_order(req, res, ctx):
                res.defer = send_sms_after_request
                res.defer = lambda r: print('I will be called too...')
                res.status = 202
        ```

- **`res.headers: tuple[2] | list[2]`** -> How headers are set i.e.
        ```py
        res.headers = 'Set-Cookie', 'Token=12345; Max-Age=8700; Secure; HttpOnly'
        ```

- **`res.status: int`** -> HTTP status code to be sent back with the response

- **`res.render(html: str, **context): Coroutine[str]`** -> Asynchronous function to help with
        rendering html. See [rendering html tutorial](html.md)

- **`res.redirect(location: str)`** -> This does this for you behind the scenes.
        ```py
        res.status = HTTPStatus.TEMPORARY_REDIRECT
        res.headers = 'Location', '/location'
        ```
        Browsers will redirect upon receipt of the header and http status above.

- **`res.abort(payload: any)`** -> If this is called then all `PRE` and `POST` [hooks](router.md) will be aborted

-----------------------
Here is a sample request handler function that shows **almost all** the functionality the `Response` object provides.
```py
async def hello(req, res: Response, ctx):
    res.status = HTTPStatus.CREATED
    res.headers = 'Content-Type', 'application/json'
    res.body = dumps({'message': 'Why hello there...'})

    # will overwrite res.body above
    await res.render('index.html')  
```

-----------------------

&nbsp;

[Next: Context of Heaven](context.md)