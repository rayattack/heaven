# Minute 1
We are assuming you have installed heaven via `pip install heaven`. If no, then go ahead and install it; If you have, then **the clock is ticking so** let's dive in.

----------------------

##### 1. Create a handler function

In a file of your choosing: i.e. `controllers.py` or `src/controllers/customers.py`
```python
import json
from http import HTTPStatus

from heaven import Request, Response, Context

async def get_one_customer(req: Request, res: Response, ctx: Context):
	id = req.params.get('id')
	res.status = HTTPStatus.CREATED
	res.body = json.dumps({"message": f"heaven is easy for customer {id}"})
```

As you can see above - your handler functions can also be async, and must accept 3 arguments that will be injected by heaven. We'll get to
them in [Minute 2](request.md), [Minute 3](response.md) and [Minute 4](context.md).

-----------------------

##### 2. Connect your handler to the heaven application

Heaven wants your application and development time to be fast so you don't need to import handler functions, just
tell your `router`, `application` where your handler function lives and heaven will load it for you.

Of course you can still import it explicitly if you are an extreme purist ;-)

```python
from heaven import Router

# create the application
router = Router()

# a string path to the python module and function name is enough
# as you can imagine this saves you time with manual imports
# if you have a lot of handlers in your project
router.GET('/v1/customers/:id', 'controllers.customers.get_one_customer')
```

All HTTP methods i.e. `GET`, `POST` etc. are all supported

-----------------------

##### 3. Run With Gunicorn or Uvicorn

```sh
# assuming your my_app.py is in a file called app.py
uvicorn my_app:router  --reload --port 9000

# or

gunicorn -w 4 -k uvicorn.workers.UvicornWorker application:router
```

-----------------------

&nbsp;

[Next: Requests to Heaven](request.md)
