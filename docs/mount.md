# Mounting Routers

Heaven allows for applications to be mounted on top of each other. See example below

<hr />

First let's create our backend api as a heaven application/router in a file called:

`api.py`
```py
from heaven import Router

api = Router()
api.GET('/v1/customers', lambda req, res, ctx:...)
```

<hr />

Next we create our frontend renderer as another heaven application/router:

`pages.py`
```py
from heaven import Router

pages = Router()

# folder where your templates are stored
pages.TEMPLATES('templates', asynchronous=False)
pages.ASSETS('assets')


pages.GET('/', lambda req, res, ctx: res.renders('index.html'))
```

<hr />

Finally we create our main heaven application that will configure database connections and mount
the `backend app` and `frontend app` on itself as mounted children:

`app.py`
```py
from heaven import Application

app = Application()

app.mount(api, isolated=True)
app.mount(pages, isolated=False)
```
