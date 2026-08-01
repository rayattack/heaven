# HeavenPG

A high-performance PostgreSQL plugin for the **Heaven** framework.

## Features
- **Connection Pooling**: Automatic management via `asyncpg`.
- **Typed Results**: Seamless `msgspec` integration for zero-overhead validation.
- **Fluent API**:
  ```python
  users = await ctx.db.fetch("SELECT * FROM users").bind(UserStruct)
  ```

## Installation
```bash
pip install heaven_pg
```

## Usage
```python
from heaven import Router
from heaven_pg import HeavenPG

app = Router()
app.plugin(HeavenPG("postgres://user:pass@localhost/db"))
```
