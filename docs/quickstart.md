# Minute 1: The Beginning ⚡

The clock is ticking. 60 seconds to a running server.

## Installation

```bash
$ pip install heaven
```

## The First Move

Create a file named `app.py`:

```python
from heaven import App

app = App()

# Handlers receive 3 arguments: Request, Response, Context
async def hello(req, res, ctx):
    res.body = "Hello from Heaven"

# Map the URL '/' to the 'hello' handler
app.GET('/', hello)
```

## Lift Off

In your terminal, run:

```bash
$ heaven fly
```

You should see:
```
INFO:     Started server process [1234]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

Open your browser to `http://localhost:8000`. 
Congratulations. Only 9 minutes left.

---

**Next:** You're flying, but now let's take control. On to **[Minute 2: The Command Line](cli.md)**.
