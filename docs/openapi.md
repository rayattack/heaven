# Min 21-22 — API Docs 📘

Because you declared your contracts on `app.schema`, Heaven already knows what every endpoint accepts and returns. Turning that into a browsable API reference is one line.

## Turn it on

```python
app.DOCS('/docs', title="Orders API", version="1.2.0")
```

That mounts two routes:

| Route | Serves |
| :--- | :--- |
| `GET /docs` | An interactive [Scalar](https://scalar.com) reference UI |
| `GET /docs/openapi.json` | The raw OpenAPI 3.1 document |

Docs are **off by default** — nothing is generated or served until you call `DOCS()`.

!!! warning "The docs page needs internet access"
    The UI loads Scalar from a CDN at render time. On an air-gapped network or a locked-down CSP the page will be blank. The JSON endpoint at `/docs/openapi.json` always works offline.

## Describing an endpoint

Everything the UI shows comes from the schema registration:

```python
class CreateItem(TypedDict):
    name: Annotated[str, "min_len=1"]
    price: Annotated[float, "min=0"]

class ItemOut(TypedDict):
    id: int
    name: str

app.schema.POST('/items',
    expects=CreateItem,
    returns=ItemOut,
    summary="Create an item",
    description="Adds an item to the inventory and returns it with its new ID.",
    group="Inventory",
)
```

| Argument | Shows up as |
| :--- | :--- |
| `expects` | The request body schema |
| `returns` | The `200` response schema |
| `summary` | The endpoint's one-line title |
| `description` | The longer prose beneath it |
| `group` | The tag the endpoint is filed under |

### Grouping

Without a `group`, Heaven tags each endpoint by its first path segment, so `/users` and `/users/:id` land together under **users**. Override it when the URL doesn't match how you want the docs organized:

```python
app.schema.GET('/system/health', returns=Health, group="Monitoring")
```

## Exporting the spec

For CI checks, client generation, or uploading to a gateway:

<div class="termy">

```console
$ heaven schema
Success! OpenAPI spec exported to swagger.json

$ heaven schema openapi-v1.json --app main:app
Success! OpenAPI spec exported to openapi-v1.json
```

</div>

## Subdomain docs

A subdomain gets its own reference, containing only its own routes:

```python
api = app.subdomain('api')
api.doc('/docs', title="Public API")     # note: .doc() on a subdomain, .DOCS() on the app
```

## Known limitations

The generated document is genuinely useful for request/response bodies, and genuinely incomplete elsewhere. Rather than let you discover this in front of a customer:

!!! danger "Path parameters are not rendered"
    Heaven emits the path key in its own routing syntax — `/users/:id` — instead of the OpenAPI form `/users/{id}`, and it emits **no `parameters` array at all**. Scalar and Swagger will therefore show the endpoint but give you no way to fill in `id`, and generated clients will not know the parameter exists.

    Until this is fixed, document path and query parameters in the `description` string.

Also absent from the generated spec today:

- **No `securitySchemes` and no `security`** — authentication is never described, so "Authorize" is unavailable in the UI.
- **Only the `200` response is emitted.** Your `422` validation failures and any error responses are undocumented.
- **No `examples`, `operationId`, `deprecated`, or `servers`.**
- **Subdomain routes collide.** The path key drops the subdomain, so the same route registered on `www` and `api` produces one entry — the second silently overwrites the first.

If your published contract has to be complete, treat `heaven schema` as a starting point and post-process the JSON.

---

**Next:** Does any of it actually work? → **[Min 23-24 — Testing with Earth](earth.md)**
