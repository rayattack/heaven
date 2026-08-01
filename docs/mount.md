# Mounting Routers

!!! note "This page has moved"
    Mounting is now covered alongside subdomains in **[Min 07-08 — Subdomains & Mounting](subdomains.md#mounting)**, which also documents hook ordering across mounts and the two limitations to know about (no path prefix, and daemons are not carried over).

## The short version

```python
# api.py
from heaven import Router
api = Router()
api.GET('/v1/customers', list_customers)
```

```python
# app.py
from heaven import Application
from api import api

app = Application()
app.mount(api)
```

`isolated=True` (the default) merges **routes only**. `isolated=False` also merges configuration, buckets, and template loaders.

[Read the full chapter →](subdomains.md#mounting)
