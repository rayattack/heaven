# The Request 📨

You've built the airport (Router), but here comes the plane. The `Request` object contains everything the client sent you, pre-parsed and ready to fly.

The signature of every handler in Heaven is:

```python
async def handler(req, res, ctx):
    ...
```

Let's dissect `req`.

## The Basics

- **`req.body`**: (bytes) The raw body.
- **`req.method`**: (str) `GET`, `POST`, etc.
- **`req.url`**: (str) The full path (e.g., `/users/1?active=true`).
- **`req.route`**: (str) The matched app route (e.g., `/users/:id`).

## Data Access

### URL Parameters (`req.params`)
When you define a route like `/users/:id:int`, Heaven parses it automatically.

```python
# Route: app.GET('/users/:id:int')
# URL: /users/42
id = req.params.get('id')
assert isinstance(id, int)
```

!!! note "Note"
    Supported types: `:int`, `:float`, `:bool`, `:uuid`, `:date`, `:datetime`, `:str` (default).

### Query Strings (`req.queries`)
Query parameters can also be typed in the route definition!

```python
# Route: app.GET('/search?limit:int&sort:str')
# URL: /search?limit=10&sort=asc

limit = req.queries.get('limit') # 10 (int)
sort = req.queries.get('sort') # 'asc' (str)
```

### JSON Bodies (`req.data`)
If you use Heaven's Schema feature, [Minute 19: Schema & Docs](schema.md), Heaven auto-validates the body and puts the result here.

```python
# Route registered with `expects=UserSchema`
user = req.data
print(user.name)
```

### Type-Safe `req.data` with Generics

`Request` is a generic class (`Request[T]`), so you can annotate your handler to get full IDE autocomplete and type checking on `req.data`:

```python
from heaven import Request, Response, Context

class User(Schema):
    name: str
    email: str

async def create_user(req: Request[User], res: Response, ctx: Context):
    user = req.data  # IDE knows this is User
    print(user.name) # autocomplete works here
```

This pairs with your schema registration — the generic parameter should match the `expects` schema:

```python
app.schema.POST('/users', expects=User)
app.POST('/users', create_user)
```

### Forms (`req.form`)
Access `application/x-www-form-urlencoded` or `multipart/form-data` uploads.

```python
form = req.form
username = form.get('username')
password = form.get('password')
file = form.get('avatar') # For file uploads
```



## Metadata

- **`req.headers`**: (dict) Lowercase header dictionary.
- **`req.cookies`**: (dict) Client cookies.
- **`req.ip`**: (Lookup) `req.ip.address` and `req.ip.port`.
- **`req.subdomain`**: (str) The subdomain (e.g., `'api'` or `'www'`).

---

**Next:** You've heard them. Now answer them. On to **[The Response](response.md)**.
