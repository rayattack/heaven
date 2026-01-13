# Minute 7: Schema & Documentation 📜

Heaven doesn't just run your code; it understands it. By using schemas, you get instant validation, auto-generated documentation, and type safety, all powered by the incredibly fast `msgspec`.

## Defining Schemas

A schema is a class that describes your data structure. Heaven exports `Schema` (a wrapper around `msgspec.Struct`) and `Constraints` (a wrapper around `msgspec.Meta`) to help you define validation rules.

```python
from typing import Annotated
from heaven import Schema, Constraints

class User(Schema):
    # Standard type hinting
    id: int
    name: str
    
    # Use Constraints for validation
    age: Annotated[int, Constraints(gt=18, lt=100)]
    
    # Use Schema.Field for default values and factories
    metadata: dict = Schema.Field(default_factory=dict)
    
    # Regular default values work too
    is_admin: bool = False
```

## The Schema Registry

Instead of cluttering your handlers with decorators, Heaven uses a "Sidecar" pattern. You register schemas on the router's `schema` property.

```python
# 1. Register the metadata
app.schema.POST('/users', 
    expects=User, 
    returns=User, 
    title="Create User",
    summary="Creates a new user in the system"
)

# 2. Define the handler (clean!)
async def create_user(req, res, ctx):
    user = req.data # Validated 'User' object
    # database logic...
    res.body = user # Heaven auto-converts this back to JSON
    
# 3. Mount the handler
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

You can control how strict Heaven is about what you send back.

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

> [!NOTE]
> **Under the Hood**: Heaven's `Schema` and `Constraints` are thin wrappers around the excellent [msgspec](https://jcristharif.com/msgspec/) library. We recommend checking out their documentation for advanced usage, performance tips, and more complex type definitions.

---

**Next:** You have built it. But does it work? On to **[Minute 8: The Earth](earth.md)**.
