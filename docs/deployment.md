# Minute 9: Deployment 🚀

You have built a masterpiece. Now it must scale.

Heaven is built on top of **ASGI** (Asynchronous Server Gateway Interface), which means it can be served by any industry-standard ASGI server like `uvicorn`, `hypercorn`, or `daphne`.

## Method 1: The Heaven Way

The simplest way to deploy is using the built-in CLI, which wraps `uvicorn` with optimal defaults.

```bash
$ heaven run main:app --host 0.0.0.0 --port 80 --no-reload --workers 4
```

- **`--no-reload`**: Vital for production performance.
- **`--workers 4`**: Run multiple processes to utilize all CPU cores.

## Method 2: Gunicorn (The Pro Way)

For robust process management, `gunicorn` with `uvicorn` workers is the industry standard.

```bash
$ pip install gunicorn
$ gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:80
```

## Method 3: Docker

Keep it contained.

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY . .
RUN pip install heaven

# Run via Heaven CLI
CMD ["heaven", "run", "main:app", "--host", "0.0.0.0", "--port", "80", "--no-reload"]
```

## Reverse Proxy

Always put **Nginx** or **Caddy** in front of your Heaven app to handle SSL, static assets, and load balancing.

---

**Next:** You made it. On to **[Minute 10: Mastery](congrats.md)**.
