# Minute 6: Rendering HTML
Heaven uses [Jinja](https://jinja.palletsprojects.com/en/3.1.x/) as its templating engine. This however
does not stop you from rolling your own preferred template engine.

You can render html templates in `asynchronous` or `asyncrhonous=False` modes.

```py
from routerling import Application

application = Application()

# application.TEMPLATES('my/templates/folder', asynchronous=False)
application.TEMPLATES('my/templates/folder')  # asynchronous=True


async def index(req, res, ctx):
    ctx.keep('message', 'Hello world!')
    await res.render('index.html', req=req, my_name='Santa')


application.GET('/', index)
```

<hr />
In your `index.html` file `Note:` heaven will inject `ctx` automatically:
```html
<h1>{{ ctx.message }}</h1><!-- injected by heaven automatically -->
<p>{{ my_name }}</p><!-- you injected this manually -->
```

You can also pass additional arguments `response.render('', *args)` the rendered template as is.

For more see [tutorial - how to use Jinja](https://jinja.palletsprojects.com/en/3.1.x/).


