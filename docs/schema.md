# Schema & API Docs

Heaven doesn't just run your code; it understands it. By using schemas, you get instant validation, auto-generated documentation, and type safety, all powered by the incredibly fast `msgspec`.

## Defining Schemas

A schema is a class that describes your data structure. Heaven exports `Schema` (a wrapper around `msgspec.Struct`) and `Constraints` (a wrapper around `msgspec.Meta`) to help you define validation rules.

```python
from heaven import Schema, Field

class User(Schema):
    id: int
    name: str
    
    # 1. Unified Bounds (min/max)
    # Field() now returns the Type + Constraints, saving you verbose typing!
    age: Field(int, min=18, max=100, desc="Must be legal age")
    tags: Field(list[str], min=1, desc="At least one tag required")
    
    # 2. Formats
    # Built-in support for 'email', 'uuid', and 'slug'
    email: Field(str, format="email", example="ray@heaven.com")
    apikey: Field(str, format="uuid", error_hint="Invalid API Key format")
    slug: Field(str, format="slug")

    # 3. Steps (Multiples)
    duration: Field(int, step=15)
    
    # 4. Defaults (via msgspec.field)
    is_active: bool = True
    metadata: dict = Schema.Field(default_factory=dict)
```

## The `Field` Helper

Heaven provides a smart `Field()` helper that simplifies validation. It returns a fully configured `Annotated` type, so you don't have to import `Annotated` or `Constraints` manually.

```python
# Instead of:
age: Annotated[int, Constraints(ge=18)]

# You write:
age: Field(int, min=18)
```

| Argument | Maps To (msgspec) | Description |
| :--- | :--- | :--- |
| `min` | `ge` / `min_length` | Minimum value (int) or length (str/list) |
| `max` | `le` / `max_length` | Maximum value (int) or length (str/list) |
| `step` | `multiple_of` | Number must be a multiple of X |
| `format` | `pattern` | Presets: `"email"`, `"uuid"`, `"slug"` |
| `desc` | `description` | Field description for OpenAPI |
| `example` | `extra_json_schema` | Example value for docs |
| `error_hint`| `extra_json_schema` | Custom error message hint |

| `error_hint`| `extra_json_schema` | Custom error message hint |

## Power Usage (Escape Hatches)

Heaven is designed to get out of your way. You are never locked into the `Field` helper.

```python
from heaven import Constraints

class PowerUser(Schema):
    # 1. Field Escape Hatch
    # Any unknown argument is passed directly to msgspec.Meta
    # e.g. 'tz' (timezone) constraint
    birthday: Field(str, format="date", tz=True)

    # 2. Raw msgspec (Bypassing Field)
    # You can use standard Annotated + Constraints logic anytime
    score: Annotated[int, Constraints(ge=0, le=100)]
    
    # 3. Complex cached structs (Advanced msgspec)
    # Schema matches msgspec.Struct behavior perfectly
    data: Annotated[bytes, Constraints(min_length=10)]
```

## The Schema Registry

Instead of cluttering your handlers with decorators, Heaven uses a "Sidecar" pattern. You register schemas on the router's `schema` property.

```python
# 0. You can mount schemas on subdomains e.g.
api = app.subdomain('api')
api.schema.POST(...)

# 1. Or on the default subdomain i.e. `www`
app.schema.POST('/users', 
    expects=User, 
    returns=User, 
    title="Create User",
    summary="Creates a new user in the system"
)

# 2. Then in your route handler(s)
async def create_user(req, res, ctx):
    # Validated 'User' object injected into `data` by heaven
    user = req.data

    # maybe some database logic?...

    # Heaven auto-converts this back to JSON
    res.body = user
    
# 3. Look ma, no decorators!
app.POST('/users', create_user)
```

## Validation

When you register an `expects` schema, Heaven automatically:

1.  **Validates** the incoming JSON body against the schema.
2.  **Aborts** with `422 Unprocessable Entity` if it's invalid (with a nice error message).
3.  **Populates** `req.data` with the validated object.

## Auto-Generated Docs (OpenAPI)

Heaven can generate a stunning interactive API reference website for you.

```python
# Mount the docs at /docs
app.DOCS('/docs', title="My API", version="1.0.0")
```

Now visit `http://localhost:8000/docs` in your browser. You will see a beautiful Scalar UI where you can test your endpoints.

### Advanced: Subdomains

You can mount docs on a specific subdomain.

```python
app.DOCS('/docs', subdomain='api')
```

### Advanced: Output Protection

**You can also control how strict Heaven is about what you send back.**

```python
app.schema.GET('/users/:id', 
    returns=User,
    protect=True,  # Strip fields not in User schema
    strict=True    # Error 500 if a required field is missing
)
```

- **`protect=True`**: Prevents data leaks. If your DB returns `password_hash` but your Schema doesn't have it, it won't be sent.
- **`partial=True`**: Allows sending only a subset of fields (good for PATCH updates).

---

!!! note "Pro Tip: Performance"
    Heaven's `Schema` is powered by **msgspec**, widely considered the fastest JSON library for Python. While standard features cover 99% of cases, you can leverage the full power of `msgspec` directly if you need e.g. zero-copy decoding or Struct caching.

---

**Next:** Yay!!! You know json kung fu. But how well? On to **[API Docs](openapi.md)**.
