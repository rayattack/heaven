# Welcome to Heaven ⚡

You are here because you want to build Python web applications without the boilerplate, the bloat, or the confusion.

**Heaven** is the super-simple, extremely fast, web framework for purists. It doesn't use "magic" decorators to hide how things work. It gives you raw ASGI speed with a developer experience that allows for **complete mastery in 10 minutes or less.**

---

## Why Heaven?

If you are tired of:
- **FastAPI's** complex dependency injection and verbose schemas.
- **Flask's** aging internal architecture and global variables.
- **Django's** massive boilerplate and rigid structure.

...then you belong in **Heaven**.

---

## Your 10-Minute Journey to Mastery

We believe you should be able to read the source code of your framework. Heaven is small enough that you *can*.

- **Minute 1**: [Quickstart](quickstart.md) - From Zero to Hello World.
- **Minute 2**: [The Request](request.md) - Understanding the incoming data.
- **Minute 3**: [The Response](response.md) - Sending data back to the world.
- **Minute 4**: [The Context](context.md) - Managing state across your app.
- **Minute 5**: [The Router & Daemons](router.md) - Routing, Hooks, and Background Jobs.
- **Minute 6**: [HTML & Assets](html.md) - Serving templates and static files.
- **Minute 7**: [Drinking Coffee](coffee.md) - You're almost a master.
- **Minute 8**: [Application Mounting](mount.md) - Building modular, large-scale apps.
- **Minute 9**: [Auth & Validation](snippets.md) - Protecting your endpoints with `.BEFORE`.
- **Minute 10**: [The Finish Line](congrats.md) - You are now a Heaven Master.

---

## Get Started Now

```sh
$ pip install heaven
```

```python
from heaven import App

app = App()

app.GET('/', lambda req, res, ctx: res.renders('index.html'))

# Run with any ASGI server
# $ uvicorn app:app --port 5000 --reload
```
