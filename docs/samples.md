## Before you go... How about some cheat codes ;-)

We use heaven extensively to power numerous enterprise microservices and have collated some practices that might help you
get there even faster.


#### Decorators
---
In this example we use the `jsonschema` library to pass along validated data to our eventual handlers

```py
from asyncio import iscoroutinefunction
from functools import wraps
from http import HTTPStatus

from jsonschema import validate
from jsonschema.exceptions import ValidationError
from ujson import dumps, loads


def expects(schema: dict):
	def wrapper(func):
		@wraps(func)
		async def delegate(r: Request, w: Response, c: Context):
			try: json = loads(r.body)
			except:
				return w.status = HTTPStatus.UNPROCESSABLE_ENTITY

			try: validate(schema, json, draft7_format_checker=True)
			except ValidationError as exc:
				w.body = dumps(exc)
				return w.status = status.BAD_REQUEST

			# little helper used in example handler below -> c.age, c.email
			for key in json: c.keep(key, json.get(key))

			# so you can wrap async and non async handler variants
			if iscoroutinefunction(func): return await func(r, w, c)
			else: return func(r, w, c)
		return delegate
	return wrapper


@expects({
	'type': 'object',
	'properties': {
		'age': {'type': 'number', 'min': 18, 'max': 180},
		'email': {'type': 'string', 'format': 'email'}
	},
	'required': ['age', 'email'],
	'additionalProperties': false,
})
async def create_customer_order(r: Request, w: Response, c: Context):
	dbpool = r.app.peek('dbpool')
	async with dbpool.acquire() as sqld:
		try:
			identifier = sqld.execute('... returning id')
		except UniqueViolationsError:
			return w.status = status.SERVICE_UNAVAILABLE

	w.status = HTTPStatus.CREATED
	w.body = dumps({
		'identifier': identifier,
		'age': c.age,
		'email': c.email
	})
```


---


This example demonstrates one of the ways Authentication might be implemented with the `pyjwt` library.
```py
from asyncpg import Pool
from jwt import decode


def private(role: str):
	"""RBAC Authorization, heaven makes it easy to also use ABAC"""
	def wrapper(func):
		@wraps(func)
		def delegate(r: Request, w: Response, c: Context):
			dbpool: Pool = r.app.peek('dbpool')
			with dbpool.acquire() as sqld:
				try: roles = await sqld.fetchval("""
					SELECT roles
					FROM privileges
					WHERE user = $1 AND action = $2
				""", c.current_user, f'{r.method.lower()}s')
				except:
					w.status = HTTPStatus.SERVICE_UNAVAILABLE
					w.body = dumps({'message': 'please try again later'})
			if role in roles: return await func(r, w, c)
	
			w.status = HTTPStatus.UNAUTHORIZED
			w.body = dumps({'message': 'insufficient privileges'})
		return delegate
	return wrapper


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
```
