# The Developer Experience Dream

## - To **Master** A Web Framework In 30 Minutes Or Less

**Heaven** was born from a simple dream: *You shouldn't need a PhD in web development to build an enterprise web application*

Web development is like a **chess board**. Many frameworks expect you to be at the level of [Magnus Carlsen](https://en.wikipedia.org/wiki/Magnus_Carlsen) before you can play (create) a **legendary** game (web application).

Other frameworks are like a crowded room shouting suggestions at you. They try to be everything for everyone. They bury you in layers of abstraction until you forget what HTTP looks like.

**Heaven is different.**

It gives you raw, unadulterated power and gets out of your way immediately with a syntax designed for
an **average developer to understand in 30 minutes** or less.

-------

*yourapp/app.py*
```py
from heaven import Router

# create the application
app = Router()

# define a route and tell heaven where it can find your handler
app.GET('/v1/games/:id', 'controllers.games.play_a_game')
```

-------

*yourapp/controllers/games.py*
```py
def play_a_game(req, res, ctx):
  res.body = 'Checkmate.'
```

-------

## Why Another Python Framework?

Tired of **Flask's** thread-local magic and aging internals.
Tired of **Django's** monolithic weight.
Tired of **FastAPI's** dependency injection labyrinth?

Looking for something **Powerful** and lightning **Fast**.
A framework that **You won't spend months learning**, cos life is too short - and more importantly
**years mastering**?

... then you belong in **Heaven**.


## Your 30-Minute Path to Mastery

Because Heaven relies on standard Python and pure HTTP concepts, you don't need a 500-page manual. You need 30 minutes.

- **[Min 01-02: The Beginning](quickstart.md)** - From Zero to Hello World.
- **[Min 03-04: The Command Line](cli.md)** - Controlling the skies with `fly` and `run`.
- **[Min 05-06: The Router](router.md)** - Understanding routes and dispatch.
- **[Min 07-08: Subdomains & Mounts](subdomains.md)** - Multi-tenancy and architecture.
- **[Min 09-10: The Request](request.md)** - Reading the user's mind.
- **[Min 11-12: The Response](response.md)** - Speaking back with authority.
- **[Min 13-14: Templating & Files](html.md)** - Rendering views and serving static assets.
- **[Min 15-16: The Context](context.md)** - Managing state like a pro.
- **[Min 17-18: Hooks & Middleware](hooks.md)** - Intercepting the pipeline power.
- **[Min 19-20: Schemas & Validation](schema.md)** - Bulletproof data validation.
- **[Min 21-22: Auto-Documentation](openapi.md)** - Free Swagger UI.
- **[Min 23-24: Testing (Earth)](earth.md)** - Testing your world without leaving it.
- **[Min 25-26: Background Tasks](daemons.md)** - Native background workers.
- **[Min 27-28: Security & Plugins](security.md)** - Signing, hashing and extending.
- **[Min 29-30: Mastery & Deployment](deployment.md)** - The final word and going live.

### Advanced Topics
- **[Plugins System](plugins.md)** - Extending Heaven with powerful integrations.

---

### Ready to Play?

```sh
$ pip install heaven
```

```python
from heaven import App

# For instance if this app could talk it might tell you:
# Hello my name is `your-app` - I am a Python web application
# I spend my time serving web requests and 
# when I am free - I spend my time dreaming of becoming a chess engine
app = App()

# The move is yours.
app.GET('/', lambda req, res, ctx: res.json({'message': 'Checkmate.'}))
```
