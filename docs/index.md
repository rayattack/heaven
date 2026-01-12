# The Developer Experience Dream

**Heaven** was born from a simple dream: *You shouldn't need a PhD in web development to build an enterprise web application*

Web development is like a **chess board**. Many frameworks expect you to be [Magnus Carlsen](https://en.wikipedia.org/wiki/Magnus_Carlsen) before you can play (create) a **legendary** game (web application).

Most modern frameworks are like a crowded room shouting suggestions at you. They try to be everything for everyone. They bury you in layers of abstraction until you forget what HTTP looks like.

**Heaven is different.**

It gives you raw, unadulterated power and gets out of your way immediately with a syntax designed for
an **average developer to understand in 10 minutes** or less.

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


## Your 10-Minute Path to Mastery

Because Heaven relies on standard Python and pure HTTP concepts, you don't need a 500-page manual. You need 10 minutes.

- **[Minute 1: The Beginning](quickstart.md)** - From Zero to Hello World.
- **[Minute 2: The Command Line](cli.md)** - Controlling the skies with `fly` and `run`.
- **[Minute 3: The Router](router.md)** - Understanding the nervous system of your app.
- **[Minute 4: The Request](request.md)** - Reading the user's mind.
- **[Minute 5: The Response](response.md)** - Speaking back with authority.
- **[Minute 6: The Context](context.md)** - Managing state like a pro.
- **[Minute 7: Schema & Docs](schema.md)** - Automatic validation and interactive docs.
- **[Minute 8: The Earth](earth.md)** - Testing your world without leaving it.
- **[Minute 9: Deployment](deployment.md)** - Going live.
- **[Minute 10: Mastery](congrats.md)** - The final word.

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
