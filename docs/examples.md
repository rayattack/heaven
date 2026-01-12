## How-To's and Code Examples

Heaven is currently being used in production by a few customer facing web products and to power
high performance microservices. Below are some of the observations and collated practices that might help provide
some guidance on code patterns possible in heaven.


#### Decorator Functions
Useful for intercepting and performing actions before the decorated function is invoked i.e. `authentication`, `dependency injection`,
or `authorization` amongst other possibilities.

---

This example demonstrates one of the ways Authentication might be implemented with the `pyjwt` library.
```py
from asyncpg import Pool
from jwt import decode


def protected(func):
	"""Authentication"""
	@wraps(func)
	def delegate(r: Request, w: Response, c: Context):
		token = r.headers.get('authorization')
		secret_key = r.app.CONFIG('SECRET_KEY')

		try: credentials = decode(token, secret_key, algorithm='HS256')
		except: return w.status = status.UNAUTHORIZED
		else: c.keep('current_user') = credentials.get('id')

		return await func(r, w, c)
	return delegate


def private(resource: str):
	"""RBAC Authorization, heaven makes it easy to also use ABAC"""
	def wrapper(func):
		@wraps(func)
		def delegate(r: Request, w: Response, c: Context):
			dbpool: Pool = r.app.peek('dbpool')
			action = r.method.lower()
			with dbpool.acquire() as sqld:
				try: roles = await sqld.fetchval("""
					SELECT roles
					FROM privileges
					WHERE user = $1 AND action = $2 AND resource = $3
				""", c.current_user, action, resource)
				except:
					w.status = HTTPStatus.SERVICE_UNAVAILABLE
					w.body = dumps({'message': 'please try again later'})
			if action in roles: return await func(r, w, c)

			w.status = HTTPStatus.UNAUTHORIZED
			w.body = dumps({'message': 'insufficient privileges'})
		return delegate
	return wrapper
```

#### Schema Validation & Documentation

Use `router.schema` to define your API contracts and `router.DOCS` to generate interactive documentation.

```py
import msgspec
from heaven import App

app = App()

class User(msgspec.Struct):
    id: int
    email: str
    role: str = "guest"

# Define your handler
async def create_user(req, res, ctx):
    user = req.data # Validated User struct
    print(f"Creating user: {user.email}")
    res.body = {"status": "created", "id": 123}

# 1. Register endpoint metadata
app.schema.POST(
    '/v1/users', 
    expects=User, 
    returns=dict, 
    summary="Create a new user",
    description="Creates a guest user by default if role is not provided."
)

# 2. Register handler
app.POST('/v1/users', create_user)

# 3. Enable Scalar Documentation
app.DOCS('/api/docs', title="User Service API")
```

The above setup provides:
- **Automatic 422 errors** for invalid JSON.
- **Static typing** in your handler via `req.data`.
- **Interactive docs** at `/api/docs`.
