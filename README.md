# Heaven : <img src="https://img.shields.io/badge/coverage-95%25-green" />

Heaven is a very very small, extremely tiny, and insanely fast [ASGI](https://asgi.readthedocs.io) web application framework. It was designed to facilitate productivity by allowing for complete mastery in 7 minutes or less.

Heaven is a very light layer around ASGI with support for application mounting and is perhaps the simplest and one of the fastest python web frameworks (biased opinion of course).


## Quickstart
1. Install with [pip](https://pip.pypa.io/en/stable/getting-started/)
```sh
$ pip install heaven
```

2. create a function to handle your http requests in a file of your choosing i.e. `patients.py` or `controllers/patients/records.py`
```py
from heaven import Request, Response, Context


async def get_record_by_id(req: Request, res: Response, ctx: Context):
    id = req.params.get('id')

    # we'll get to this in a minute
    dbconn = req.app.peek('dbconnection')
    results = await dbconn.execute('select * from patients where id = 1000')

    # req, res, ctx are available in your jinja templates
    ctx.keep('results', results)
    await res.render('patients.html')
```


3. Create your heaven application and connect your request handler e.g. in `src/example.py`
```py
from heaven import App  # also available as Router, Application


router = Router()


# note that you did not need to import your request handler, just giving heaven
# the path to your handler as a string is enough
router.GET('/v1/patients/:id', 'controllers.patients.records.get_record_by_id')
```


4. You can run with uvicorn, gunicorn or any other asgi HTTP, HTTP2, and web socket protocol server of your choice.
```sh
$ uvicorn app:example --reload
 * Running on http://127.0.0.1:8000
```


## Contributing

For guidance on how to make contributions to Routerling, see the [Contribution Guidelines](contributions.md)


## Links

- Documentation [Go To Docs](https://rayattack.github.io/heaven)
- PyPi [https://pypi.org/project/heaven](https://pypi.org/project/heaven)
- Source Code [Github](https://github.com/rayattack/heaven)
