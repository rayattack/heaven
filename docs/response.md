#### 2. Response
All handlers receive this as the second argument i.e. **`...(..., w: Response, ...)`**

The `Response` object provides a ton of goodies to help with responding to http requests.

-----------------------

- **`res.body: any = 'hello'`** -> This will be sent back as the body of the response

- **`res.headers: tuple[2] | list[2]`** -> How headers are set i.e.
        ```py
        w.headers = 'Set-Cookie', 'Token=12345; Max-Age=8700; Secure; HttpOnly'
        ```

- **`res.status: int`** -> HTTP status code to be sent back with the response

- **`res.html(html: str, **context): Coroutine[str]`** -> Asynchronous function to help with rendering html. See [rendering html tutorial](html.md)

- **`res.redirect(location: str)`** -> Types this http redirect code for you behind the scenes.
        ```py
        res.status = HTTPStatus.TEMPORARY_REDIRECT
        res.headers = 'Location', '/location'
        ```

- **`res.abort(payload: any)`** -> If this is called then all `PRE` and `POST` [hooks]() will be aborted

-----------------------
Here is a sample request handler function that shows **almost all** the functionality the `Request` object provides.
```py
async def hello(req, res: Response, ctx):
    res.status = HTTPStatus.CREATED
    res.headers = 'Content-Type', 'application/json'
    res.body = dumps({'message': 'Why hello there...'})
```