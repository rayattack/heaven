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

!!! tip "Pro Tip: Developer Speed"
    As your application grows, importing hundreds of handlers at the top of your file becomes tedious. Heaven lets you pass the **import path as a string**.
    
    ```python
    # Heaven lazy-loads this module only when needed! 
    # No more giant import lists.
    app.GET('/profile', 'handlers.users.get_profile')
    ```

## Lift Off

In your terminal, run:

```bash
$ heaven fly
```

OR

```bash
$ heaven run app:app
```

You should see:
```
INFO:     Started server process [1234]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

Open your browser to `http://localhost:8000`. 
Congratulations. Only 28 minutes left.

---

**Next:** You're flying, but now let's take control. On to **[The Command Line](cli.md)**.
