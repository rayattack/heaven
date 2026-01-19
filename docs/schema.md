# Schema & API Docs

Heaven doesn't just run your code; it understands it. By using schemas, you get instant validation, auto-generated documentation, and type safety, all powered by the incredibly fast `msgspec`.

## Defining Schemas

A schema is a class that describes your data structure. Heaven exports `Schema` (a wrapper around `msgspec.Struct`) and `Constraints` (a wrapper around `msgspec.Meta`) to help you define validation rules.

```python
from typing import Annotated
from heaven import Schema, Field

class User(Schema):
    id: int
    name: str
    
    # 1. Bounds (Values vs Lengths)
    # Use 'min'/'max' for numeric values (>=, <=)
    age: Annotated[int, Field(min=18, max=100, desc="Must be legal age")]
    
    # Use 'min_len'/'max_len' for sequence lengths
    tags: Annotated[list[str], Field(min_len=1, desc="At least one tag required")]
    
    # 2. Formats
    # Built-in support for 'email', 'uuid', and 'slug'
    email: Annotated[str, Field(format="email", example="ray@heaven.com")]
    apikey: Annotated[str, Field(format="uuid", error_hint="Invalid API Key format")]
    slug: Annotated[str, Field(format="slug")]

    # 3. Steps (Multiples)
    duration: Annotated[int, Field(step=15)]
    
    # 4. Defaults (via msgspec.field)
    is_active: bool = True
    metadata: dict = Schema.Field(default_factory=dict)
```

## The `Field` Helper

Heaven provides a smart `Field()` helper that simplifies validation. It returns `msgspec.Meta` constraints configured for your needs.

| Argument | Maps To (msgspec) | Description |
| :--- | :--- | :--- |
| `min` / `max` | `ge` / `le` | Numeric constraints (>=, <=) |
| `min_len` / `max_len` | `min_length` / `max_length` | Sequence length constraints |
| `step` | `multiple_of` | Number must be a multiple of X |
| `format` | `pattern` | Presets: `"email"`, `"uuid"`, `"slug"` |
| `desc` | `description` | Field description for OpenAPI |
| `example` | `extra_json_schema` | Example value for docs |
| `error_hint`| `extra_json_schema` | Custom error message hint |

## Advanced Patterns

Heaven's `Field` helper is designed to scale with your needs. It seamlessly integrates with `msgspec`'s advanced features.

### 1. Nested Arrays & Matrices

You can apply constraints to the list itself AND the items within it.

```python
class BatchUpload(Schema):
    # The LIST must have 1-100 items.
    # Each ITEM must be a string of length 3-50.
    tags: Annotated[
        list[Annotated[str, Field(min_len=3, max_len=50)]], 
        Field(min_len=1, max_len=100)
    ]
```

### 2. Complex Unions (Polymorphism)

Validate data that can be one of multiple types, each with its own rules.

```python
class SearchQuery(Schema):
    # ID can be a positive Integer OR a UUID String
    id: Annotated[int, Field(min=1)] | Annotated[str, Field(format="uuid")]
```

### 3. Timezones & Dates

Native `msgspec` constraints (like `tz`) pass straight through `Field`.

```python
from datetime import datetime

class Event(Schema):
    # Enforce timezone-aware datetimes (rejects naive inputs)
    start_time: Annotated[datetime, Field(tz=True)]
```

### 4. The Escape Hatch (Raw Access)

If you strictly prefer raw `msgspec`, you can bypass `Field` entirely.

```python
from heaven import Constraints

class RawMetal(Schema):
    # Pure msgspec code works 100% of the time
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
