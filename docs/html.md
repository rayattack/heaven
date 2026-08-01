# Min 13-14 — Templates & Assets 🎨

Heaven renders HTML with [Jinja2](https://jinja.palletsprojects.com/), asynchronously by default.

## Static files

Point a URL prefix at a folder on disk:

```python
app.ASSETS('assets')                 # serves ./assets at /assets/*
app.ASSETS('assets', '/static/*')    # serves ./assets at /static/*
```

`assets/logo.png` is now at `http://localhost:8000/assets/logo.png`.

!!! note "`ASSETS` stays inside its folder"
    The requested path is resolved before anything is opened, and requests that land outside the asset folder return 404, whether they got there via `..` segments, an absolute path, or a symlink pointing out of the tree. `..` segments that stay inside the folder still resolve normally. `ASSETS` is a wrapper over `res.file(..., within=...)`, so the guarantees are the same ones documented in [Serving Files](files.md#confining-a-read-with-within).

    **In production, serve static files from Nginx, Caddy, or a CDN anyway.** It is faster than routing them through the app.

!!! tip "Paths are relative to the working directory"
    By default the folder is resolved from wherever the process was started, which breaks when you run from a different directory. Anchor it to a file instead:

    ```python
    app.ASSETS('assets', relative_to=__file__)
    ```

## Templates

```python
app.TEMPLATES('templates')
```

Then render into the response body:

```python
async def profile(req, res, ctx):
    ctx.keep('user_name', 'Ada')
    await res.render('profile.html', title='Your Profile')
```

| Method | Use when |
| :--- | :--- |
| `await res.render(name, **vars)` | the normal case — async rendering |
| `res.renders(name, **vars)` | templates configured with `asynchronous=False` |
| `await res.interpolate(name, **vars)` | you want the rendered **string** back instead of setting the body |

`TEMPLATES()` also takes `relative_to=__file__`, an `escape=` override, and `prefix=` for namespacing (below).

## What every template can see

Heaven injects the three request objects into every template automatically:

```html
<h1>Hello, {{ ctx.user_name }}</h1>
<p>You are visiting: {{ req.url }}</p>
<p>Status: {{ res.status }}</p>

<title>{{ title }}</title>   <!-- anything you passed to render() -->
```

So `ctx` doubles as your template context — anything a `BEFORE` hook stashed there is available in the template without being threaded through `render()`.

## Combining template folders

Call `TEMPLATES()` more than once and the folders are searched in order. Add a `prefix` to namespace a set — useful when mounting apps that each ship their own templates and might collide on `index.html`.

```python
app.TEMPLATES('templates')
app.TEMPLATES('blog/templates', prefix='blog')

await res.render('index.html')        # from ./templates
await res.render('blog/index.html')   # from ./blog/templates
```

---

**Next:** Sharing state between hooks and handlers → **[Min 15-16 — The Context](context.md)**
