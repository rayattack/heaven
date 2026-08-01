# Min 03-04 — The Command Line 🛠️

You've met `heaven fly`. The CLI does four more things, and two of them will change how you debug.

<div class="termy">

```console
$ heaven
usage: heaven [-h] {fly,run,routes,handlers,schema} ...

Heaven CLI - The divine interface for your web framework.

positional arguments:
  {fly,run,routes,handlers,schema}
    fly                 Zero-config auto-discovery run
    run                 Run a specific application
    routes              Show all registered routes
    handlers            Deep inspection of handlers
    schema              Export OpenAPI spec to JSON
```

</div>

## `fly` — zero config

Hunts for an `App` or `Router` in `app.py`, `main.py` or similar, and runs it.

```bash
heaven fly
heaven fly --port 8080 --host 0.0.0.0
```

!!! note "`fly` is for development"
    Auto-reload is always on. Use `run` for anything else.

## `run` — explicit

```bash
heaven run main:app
heaven run api.server:application --host 0.0.0.0 --port 8000 --no-reload
```

The `module:variable` form is the same one uvicorn and gunicorn use.

## `routes` — what's actually registered

The fastest way to answer "why is this 404-ing". Prints every path, method, and subdomain as a table.

```bash
heaven routes
heaven routes --app main:app
```

!!! tip "Check `routes` before you debug a 405"
    A path that exists under a different method returns 405 with an `Allow` header. If a `POST` is coming back 405, this table shows you which methods that route actually registered.

## `handlers` — where is this code?

Tunnels through decorators, `functools.partial`, and closures to find the **original** function and its source file. Invaluable in a codebase that registers handlers as strings.

```bash
heaven handlers                # every handler and its file location
heaven handlers /api/users     # the source of one endpoint, in your terminal
```

## `schema` — export OpenAPI

```bash
heaven schema                          # -> swagger.json
heaven schema openapi-v1.json          # custom filename
```

For CI contract checks or client generation. See [API Docs](openapi.md) — including what the generated spec does and doesn't contain.

---

**Next:** Directing the traffic → **[Min 05-06 — The Router](router.md)**
