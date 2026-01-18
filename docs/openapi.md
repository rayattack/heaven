# Auto-Generated API Docs (OpenAPI)

Heaven automatically generates an OpenAPI 3.0 (Swagger) specification for your API, derived directly from your code and schemas.

## Enabling Documentation

The documentation UI is not enabled by default to keep things lightweight. You enable it by mounting the docs endpoint.

```python
# Serves Swagger UI at /docs and schema at /docs/openapi.json
app.DOCS(route='/docs', title="My API", version="1.0.0")
```

## Connecting Schemas

The documentation power comes from the `SchemaRegistry`. When you register a route with `.schema`, Heaven learns what the endpoint expects and returns.

```python
class CreateItem(Schema):
    name: str
    price: float

class ItemResponse(Schema):
    id: int
    name: str

app.schema.POST(
    '/items',
    expects=CreateItem,
    returns=ItemResponse,
    summary="Create a new item",
    description="Adds a new item to the inventory and returns it with an ID.",
    group="Inventory" # Groups endpoints in the UI
)
```

## Grouping

Heaven automatically groups endpoints based on the URL structure (e.g. `/users` and `/users/:id` are grouped under "Users").

You can override this with the `group` parameter:

```python
app.schema.GET('/system/health', group="Monitoring", ...)
```

## Subdomain Documentation

If you are using subdomains, you can enable documentation specifically for that subdomain.

```python
api = app.subdomain('api')
# This documentation will ONLY show routes registered to the 'api' subdomain
api.doc('/docs', title="Public API")
```

**Next:** You must have written a lot of code by now, but does it work? Let's see on **[Earth](earth.md)**.