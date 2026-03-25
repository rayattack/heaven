# CLAUDE.md

## Project Overview

Heaven is an async Python (3.6+) ASGI web framework. "Stupid simple, blazing fast, get out of your way immediately."

- **Package:** `heaven` (PyPI), v1.3.14
- **Entry point:** `heaven.cli:main`
- **Build system:** Poetry
- **License:** MIT
- **Repo:** `rayattack/heaven`

## Architecture

Core source is in `heaven/`. Key files:

- `router.py` — Central app class (aliased as `App`, `Application`, `Server`), routing, schema baking, lifecycle, subdomain management
- `request.py` — `Request(Generic[T])` with parsed params, queries, cookies, form, validated `data`
- `response.py` — Response building: body, headers, streaming, SSE, file serving, defer, abort
- `context.py` — Per-request scoped storage with typed `Key[T]`
- `earth.py` — Built-in test client
- `schema.py` — Re-exports pytastic
- `security.py` — HMAC-SHA256 signed sessions, `SecureSerializer`
- `form.py` — Multipart/urlencoded form parsing
- `cli.py` — CLI entry point
- `utils.py` — `Lookup` (dot-notation dict wrapper), helpers
- `errors.py` — Framework exceptions

## Key Design Decisions

- **Sidecar pattern:** Schema registration (`app.schema.POST(...)`) is separate from handler registration (`app.POST(...)`). One registration drives both runtime validation and OpenAPI doc generation.
- **String discovery:** Routes accept module path strings (`"handlers.users.list_users"`) that resolve lazily at registration time.
- **Handler signature:** Always `(req, res, ctx)` — sync or async.
- **`Request[T]` generics:** Annotate handlers with `Request[YourSchema]` for IDE autocomplete on `req.data`. This is a convention — not enforced at runtime.
- **Middleware:** BEFORE/AFTER hooks, not wrapping middleware. Use `ctx` to share state between them.

## Commands

```bash
# Install dependencies
poetry install

# Run tests
python -m pytest tests/

# Run the dev server (if app is in main.py)
uvicorn main:app --reload

# Or via CLI
heaven
```

## Testing

Tests are in `tests/` using `unittest.IsolatedAsyncioTestCase`. Run with pytest:

```bash
python -m pytest tests/ -v
```

The built-in test client is `app.earth.test()`.

## Plugins

In `plugins/` directory:
- `heaven_pg` — PostgreSQL
- `heaven_aaa` — Authentication/Authorization

## Documentation

Full docs site in `docs/` (built with MkDocs). Config in `mkdocs.yml`.

LLM-optimized reference in `.heaven` file at project root.

## Style

- No decorators on handlers
- Prefer string discovery over direct imports for route handlers
- `orjson` for JSON serialization (implicit dependency)
- Framework re-exports pytastic types: `Schema`, `Field`, `Constraints`
