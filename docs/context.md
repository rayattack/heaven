`View Source Code: ` [`Open on GitHub`](https://github.com/rayattack/heaven/blob/main/heaven/context.py)

# Minute 4


### Object \#3. Context
All handlers receive this as the third argument i.e. **`...(..., ..., c: Context)`** to help with preserving state across
    multiple handlers (i.e. from when a request is received to when a response is sent).

- **`c.keep(alias: str, value: any)`** -> Save something that can be retrieved via [Python descriptor]() semantics. i.e. `c.alias` will return the kept value.


```py
from functools import wraps


def example(func):
    @wraps(func)
    async def wrapper(req, res, ctx):
        ctx.keep('user_id', 1986)
        func(req, res, ctx)
    return wrapper


@example
def get_user(req, res, ctx):
    assert ctx.user_id == 1986
```

-----------------------

&nbsp;

[Next: Application](router.md)