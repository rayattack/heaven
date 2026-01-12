# Minute 2: The Command Line 🛠️

In Minute 1, you met `heaven fly`. But you don't just want to fly, you want to pilot. Heaven's CLI is your cockpit. It is precise, informative, and explicitly typed.

## The `heaven` Command

Type `heaven` (or `heaven -h`) to see your controls.

```bash
$ heaven
usage: heaven [-h] {fly,run,routes,handlers,schema} ...

Heaven CLI - The divine interface for your web framework.

positional arguments:
  {fly,run,routes,handlers,schema}
                        Available commands
    fly                 Zero-config auto-discovery run
    run                 Run a specific application
    routes              Show all registered routes
    handlers            Deep inspection of handlers
    schema              Export OpenAPI spec to JSON
```

## 1. Zero-Config: `heaven fly`

The `fly` command is for when you just want to code. It automatically hunts for `app.py`, `main.py`, or similar files in your current directory and launches the first `App` or `Router` instance it finds.

```bash
# Just fly.
$ heaven fly

# Fly on a different port.
$ heaven fly --port 8080 --host 0.0.0.0
```

> [!NOTE]
> `heaven fly` always enables auto-reload. It is designed for development.

## 2. Explicit Control: `heaven run`

When you go to production or have a complex project structure, you need `run`. This command stops the magic guessing game and does exactly what you tell it.

```bash
# Run the 'app' object in 'main.py'
$ heaven run main:app

# Production mode (no reload, multiple workers)
# Note: Heaven wraps uvicorn, so for advanced deployment you can use uvicorn directly too.
$ heaven run main:app --no-reload --host 0.0.0.0 --port 80
```

## 3. Deep Introspection

Heaven wants you to know your app better than you know yourself.

### View Your Routes
See every path, method, subdomain, and protection status in a beautiful table.

```bash
$ heaven routes
# or specify the app path explicitly
$ heaven routes --app main:app
```

### Inspect Your Handlers
Have you ever forgotten where a specific endpoint is defined? `handlers` tunnels through decorators, partials, and closures to find the *original* source code.

```bash
# Interactive map of all handlers and their file locations
$ heaven handlers

# View the source code of a specific handler right in your terminal
$ heaven handlers /api/users
```

### Export Schema
Need your OpenAPI spec for a CI pipeline or client generator?

```bash
$ heaven schema
# outputs to swagger.json by default

$ heaven schema openapi-v1.json
```

---

**Next:** Now that you can control the server, let's learn how to direct the traffic. On to **[Minute 3: The Router](router.md)**.
