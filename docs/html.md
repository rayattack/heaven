# Templating & Files

Heaven uses [Jinja2](https://jinja.palletsprojects.com/) for templating, but keeps it async and non-blocking.

## Serving Static Files

First, let's serve your CSS and images.

```python
# Map /static to 'assets' folder
# 'OR' serve everything in 'assets' folder at '/static' URL
app.ASSETS('/static', 'assets')
```

Now `assets/logo.png` is available at `http://localhost:8000/static/logo.png`.

## Enabling Templates

Tell Heaven where your templates live.

```python
# 'templates' is the folder name
app.TEMPLATES('templates')
```

## Rendering HTML

You can render templates asynchronously.

```python
async def index(req, res, ctx):
    ctx.keep('user_name', 'Visitor')
    
    # Render 'index.html'
    # You can pass extra variables directly (e.g. title)
    await res.render('index.html', title="Welcome Home")
```

### Automatic Context

Heaven automatically injects the three musketeer objects into **every** template:

- `req`: The current Request object `a.k.a` **Portos**.
- `res`: The current Response object `a.k.a` **Athos**.
- `ctx`: The current Context object `a.k.a` **Aramis**.

> PS: D'Artagnan is not a musketeer but in the spirit of camarederie he can be the **Router**

**In your `index.html`:**

```html
<!-- Access variables from ctx -->
<h1>Hello, {{ ctx.user_name }}</h1>

<!-- Access request info -->
<p>You are visiting: {{ req.url }}</p>

<!-- Access response info -->
<p>Status: {{ res.status }}</p>

<!-- Access passed variables -->
<title>{{ title }}</title>
```

---


**Next:** We've covered the basics. Now let's superpower your app with Schemas. On to **[Interceptors](hooks.md)**.