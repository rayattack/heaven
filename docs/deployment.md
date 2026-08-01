# Min 29-30 — Deployment 🚀

Heaven is an ASGI application, so anything that serves ASGI serves Heaven: `uvicorn`, `hypercorn`, `granian`, `daphne`.

## The pre-flight checklist

Run through this before the first public request:

- [x] `App(debug=False)` — otherwise tracebacks are served to clients
- [x] `SECRET_KEY` read from the environment, never committed
- [x] Static files served by your proxy, not `app.ASSETS()` ([why](html.md#static-files))
- [x] A body-size limit in the proxy — Heaven has none
- [x] `--no-reload`
- [x] Security headers ([copy-paste hook](production.md))

## Running it

=== "Heaven CLI"

    ```bash
    heaven run main:app --host 0.0.0.0 --port 8000 --no-reload
    ```

    A thin wrapper over uvicorn. Fine for a container that already has a process manager around it.

=== "Uvicorn"

    ```bash
    uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
    ```

=== "Gunicorn"

    ```bash
    gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
    ```

    Gunicorn's process supervision — restarting workers that die or leak — is what you want on a long-running host.

!!! warning "`app.listen()` is broken on modern uvicorn"
    `Router.listen()` passes a `debug=` argument that uvicorn removed years ago, so it raises `TypeError`. Use the CLI or run uvicorn directly.

!!! danger "Workers multiply your daemons"
    Each worker process runs its own copy of every [daemon](daemons.md). With `--workers 4`, a cleanup daemon runs four times on every tick. Either run daemons in a single dedicated process, or make them idempotent and safe to race.

## Docker

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1

CMD ["heaven", "run", "main:app", "--host", "0.0.0.0", "--port", "8000", "--no-reload"]
```

!!! tip "Pin `orjson` yourself"
    Heaven imports `orjson` but does not currently declare it as a dependency, so a clean install can fail at `import heaven`. Put `orjson` in your own `requirements.txt` until that's fixed upstream.

## Behind a proxy

Put Nginx or Caddy in front for TLS, static files, and body limits:

```nginx
server {
    listen 443 ssl http2;
    server_name example.com;

    client_max_body_size 10M;          # Heaven has no limit of its own

    location /static/ {
        alias /var/www/app/assets/;    # faster, and avoids app.ASSETS()
        expires 30d;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_http_version 1.1;         # websockets
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

There's a fuller treatment — security headers, CSP, secrets — in [Going to Production](production.md).

---

**Next:** You made it → **[Mastery](congrats.md)**
