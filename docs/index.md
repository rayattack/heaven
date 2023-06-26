## Welcome To Heaven
You are probably here because you want to build a web application using Python. Well, Welcome to heaven - the super
simple, extremely fast, web framework for purists.

Building a web application with heaven is stupid simple as the code snippet below shows


```py
from heaven import Router  # also available as App, Application

# create your web app i.e. a simple router/multiplexer
app = Router()
```

And to run your new app from heaven?

```sh
$ uvicorn app:app --port 5000 --reload
```

## Heaven's Goals vs Building Useful Apps
Heaven was designed with 3 goals in mind. The example above creates a simple heaven app but it does not do anything useful.

But, what do we mean when we say an app is useful, and how does it relate to Heaven's Goals?

In our opinion a **useful app(s)**:

1. Solves a problem
2. Is extremely simple to learn (Mastery in 10mins or less)
3. Is optimized for speed

These are also Heaven's goals.

- Heaven solves the framework mastery problem - Enabling engineers build APIs and Web Applications that also embody Heaven's goals.

- Is super simple to learn - in line with it's goal of `Mastery in 10 mins or less`. If you find a  python web framework easier to learn than Heaven, use it.

- Faster than Django, Flask, Pyramid etc. and will get even faster as it is optimized further.


## Why Another Python Web Framework?
Because we needed something small enough to be learnt completely by new engineers in less than 10
minutes. Complete mastery with no gray spots.

&nbsp;

## Don't Have 10 Minutes To Spare?
----------------------------------------------
#### Here's a quick crash course on heaven in 5 minutes


##### 1. Create a handler function

```python
import json
from http import HTTPStatus

from heaven import Request, Response, Context

async def get_one_customer(r: Request, w: Response, c: Context):
	id = r.params.get('id')
	w.status = HTTPStatus.CREATED
	w.body = json.dumps({"message": f"heaven is easy for customer {id}"})

```


##### 2. Connect your handler to the heaven application

```python
from heaven import Router

# create the application
router = Router()

# connect it to a route
router.GET('/v1/customers/:id', get_one_customer)
router.POST('/v1/customers', lambda req, res, ctx:...)
router.DELETE('/v1/customers/:id', lambda req, res, ctx:...)
```

All HTTP methods i.e. `PUT`, `PATCH`, `OPTIONS` etc. are all supported



##### 3. Run With Gunicorn or Uvicorn

```sh
# assuming your my_app.py is in a file called app.py
uvicorn my_app:router  --reload --port 9000
```


&nbsp;

-----------------------------------------------

## Okay, What Next?

- Minute 1: [Quickstart](quickstart.md) : Toe in the water

- Minute 2: [Heaven Application](router.md)

- Minute 3: [Request to Heaven](request.md)

- Minute 4: [Responses from Heaven](response.md)

- Minute 5: [Context of Heaven](context.md)

- Minute 6: [Rendering HTML Templates &amp; Public Assets](html.md)

- Minute 7: [Drink some coffee](coffee.md)

- Minute 8: [Mounting Applications](mount.md)

- Minute 9: [Authentication &amp; Data Validation Guidelines/Code Snippets](snippets.md)

- Minute 10: [Congratulate Yourself](congrats.md)
