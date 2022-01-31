# Routerling : <img src="https://img.shields.io/badge/coverage-95%25-green" />

Routerling is a very very small, extremely tiny, and insanely fast [ASGI](https://asgi.readthedocs.io) web application framework. It was designed to facilitate productivity by allowing for complete mastery in 7 minutes or less.

Routerling is a very light layer around ASGI with support for application mounting and is perhaps the simplest and one of the fastest python web frameworks (biased opinion of course).


## Installling
Install with [pip](https://pip.pypa.io/en/stable/getting-started/)
```sh
$ pip install routerling
```

## A Simple Example
<hr/>

```py
from routerling import Router


async def index(req, res, ctx):
    res.body = 'Hello, World!'


router = Router()


router.GET('/', index)
```

You can run with uvicorn, gunicorn or any other asgi HTTP, HTTP2, and web socket protocol server of your choice.
```sh
$ uvicorn main:router --reload
 * Running on http://127.0.0.1:8000
```


## Contributing

For guidance on how to make contributions to Routerling, see the [Contribution Guidelines](contributions.md)


## Links

- Documentation [Go To Docs](https://rayattack.github.io/routerling)
- PyPi [https://pypi.org/project/routerling](https://pypi.org/project/routerling)
- Source Code [Github](https://github.com/rayattack/routerling)
