# Minute 9: Guidelines and Code Snippets
Heaven is extremely unopinionated. Using python [decorators](); this section
shows a few ways to combine standard python
libraries like [pydantic](), [PyJWT]() etc. with heaven.


## Authentication Example

```py
from functools import wraps
from inspect import iscoroutinefunction

# typing is amazing let's use it as much as we can
from heaven import Context, Request, Response


def protect(func):
    @wraps(func)
    async def delegate(req: Request, res: Response, ctx: Context):
        token = req.headers.get('authorization')

        # use your preferred jwt or other validation lib/scheme here
        if not token:
            res.status = HTTPStatus.UNAUTHORIZED
            res.body = 'Whatever body you want'
            return

        ctx.keep('user', {...})
        if iscoroutinefunction(handler): await func(req, res, ctx)
        else: func(req, res, ctx)
    return delegate


# use decorator to protect handler(s) of choice
@protect
async def get_customer_info(req: Request, res: Response, ctx: Context):
    res.body = {}
```


## Data Validation Example

```py
from heaven import ...  # necessary imports here
from pydantic import BaseModel


class Guest(BaseModel):
    email: EmailStr
    password: str


def expects(model: BaseModel):
    async def delegate(req: Request, res: Response, ctx: Context):
        try:
            data = loads(req.body)
            guest = Guest(**data)
        except:  # be more specific with exceptions in production code
            res.status = HTTPStatus.BAD_REQUEST
            return
        ctx.keep('guest', Guest)
    return delegate


@expects(Guest)
async def do_login_with_email(req: Request, res: Response, ctx: Context):
    guest: Guest = ctx.guest
    print(guest.email)
    print(guest.password)
```