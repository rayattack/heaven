
# Subdomains

Heaven makes it incredibly easy to build multi-tenant applications or segregate your API using subdomains.

## Basics

The `app.subdomain(name)` method returns a **proxy object** (a `SubdomainContext`) that allows you to register routes, hooks, and schemas specifically for that subdomain.

```python
# Create a proxy for the 'admin' subdomain
admin = app.subdomain('admin')

# Register a route
admin.GET('/dashboard', admin_dashboard)
```

Now, `http://admin.example.com/dashboard` will serve the dashboard, but `http://example.com/dashboard` will 404.

## Consistency & Proxies

It is important to understand that `app.subdomain('name')` returns a **new proxy object** each time, but they all point to the **same shared state** within the application.

This means you can call `app.subdomain('api')` in multiple places (even different files), and they will all contribute to the same routing table.

```python
# In users.py
api = app.subdomain('api')
api.GET('/users', list_users)

# In posts.py
api = app.subdomain('api') # This is safe!
api.GET('/posts', list_posts)
```

Both `/users` and `/posts` are immediately registered to the `api` subdomain. There is no need to pass the `api` object around; you can just re-instantiate the proxy whenever you need it.

## Subdomain Schemas

You can also enforce schemas specifically for a subdomain. This is useful when your main site and your API have different validation rules or when you want formatted OpenAPI docs for your API subdomain.

The `SubdomainContext` exposes a `.schema` property which, similarly, returns a consistent proxy to the registry.

```python
from heaven import Schema

class CreateUser(Schema):
    username: str

api = app.subdomain('api')

# Register schema-validated route on the API subdomain
api.schema.POST('/users', expects=CreateUser)
api.POST('/users', create_user_handler)
```

Just like the router itself, `api.schema` is safe to call multiple times.

## Hooks

You can also register middleware (hooks) that only run for a specific subdomain.

```python
admin = app.subdomain('admin')

async def require_admin(req, res, ctx):
    if not user.is_staff:
        res.status = 403
        res.abort("Forbidden")

# This hook ONLY runs for requests to admin.example.com
admin.BEFORE('/*', require_admin)
```
