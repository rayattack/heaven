# Minute 1
We are assuming you have installed heaven via `pip install heaven`. If no, then go ahead and install it; If you have, then **the clock is ticking so** let's dive in.

----------------------

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

As you can see above - your handler function can be async if you desire and must accept 3 arguments that will be injected by heaven. We'll get to
them in [Minute 1](request.md), [Minute 2](response.md) and [Minute 3](context.md).

-----------------------

##### 2. Connect your handler to the heaven application

```python
from heaven import Router

# create the application
router = Router()

# connect it to a route
router.GET('/v1/customers/:id', get_one_customer)
```

All HTTP methods i.e. `GET`, `POST` etc. are all supported

-----------------------

&nbsp;

[Next: Requests to Heaven](request.md)