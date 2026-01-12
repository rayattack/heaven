# Heaven ⚡ : <img src="https://img.shields.io/badge/coverage-95%25-green" />

**Heaven** is the absolute minimal, insanely fast [ASGI](https://asgi.readthedocs.io) web framework for Python purists. It doesn't just get out of your way; it vanishes, leaving you with raw performance and total control.

> "Mastery in 10 minutes or less. No grey spots, just pure Python."

<hr/>

### Why Heaven?

| Feature | Heaven | FastAPI | Flask | Django |
| :--- | :---: | :---: | :---: | :---: |
| **Learning Curve** | 10 Mins | High | Low | Extreme |
| **Performance** | ⚡⚡⚡ | ⚡⚡ | ⚡ | 🐢 |
| **Boilerplate** | Zero | Medium | Low | Massive |
| **Mastery** | Complete | Partial | High | Low |
| **Background Jobs**| Native (Daemons) | External | External | External |

1. **Stupid Simple**: Built for engineers who hate bloat. If you know Python, you already know Heaven.
2. **Blazing Fast**: A thin layer over ASGI, optimized for high-concurrency and low-latency.
3. **Batteries Included (The right ones)**: Native support for application mounting, centralized hooks (`.BEFORE`/`.AFTER`), and powerful background **Daemons**.
4. **Transparent**: No magic decorators that hide logic. Just clear, explicit routing.

<hr/>

## Quickstart in 60 Seconds

1. **Install** 
```sh
$ pip install heaven
```

2. **Code**
```python
from heaven import App, Request, Response, Context

app = App()

# Centralized Auth / Pre-processing
async def auth(req, res, ctx):
    if not req.headers.get('Authorization'):
        res.abort('Unauthorized', status=401)

app.BEFORE('/api/*', auth)

# Simple Handler
async def welcome(req, res, ctx):
    res.body = {"message": "Welcome to Heaven"}

app.GET('/api/v1/welcome', welcome)

3. **Protect** (Automatic OpenAPI)
```python
from heaven import Schema

class User(Schema):
    name: str

app.schema.POST('/user', expects=User, summary="Create User")
app.DOCS('/docs')
```

4. **Fly** (CLI)
Heaven comes with a beautiful, zero-config CLI.
```bash
pip install heaven

# Auto-discovery & run with reload
heaven fly

# Visualize your API structure
heaven routes
```

5. **Daemon** (Background)
```python
async def pulse(app):
    print("Heartbeat...")
    return 5 # Run every 5 seconds

app.daemons = pulse
```

6. **Run** (Standard)
```sh
$ uvicorn app:app --reload
```

<hr/>

- **Full Documentation**: [https://rayattack.github.io/heaven](https://rayattack.github.io/heaven)
- **PyPi**: [https://pypi.org/project/heaven](https://pypi.org/project/heaven)
- **Source**: [Github](https://github.com/rayattack/heaven)

## Contributing

We love builders. See the [Contribution Guidelines](contributions.md).

