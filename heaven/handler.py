from typing import Generic, TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from heaven.context import Context
    from heaven.request import Request
    from heaven.response import Response


T = TypeVar('T')


class Handler(Generic[T]):
    """Base class for handlers registered as `'package.module.Class#method'`.

    Heaven builds one instance per request and calls the named method on it, so
    `self` is request scoped and never shared between requests in flight:

        from heaven import Handler

        class Orders(Handler):
            async def index(self):
                self.res.body = await self.req.app.peek('db').orders()

        app.GET('/orders', 'handlers.orders.Orders#index')

    The same three objects a function handler is handed arrive as attributes, so
    the two styles are the same contract written differently. Subclassing is what
    types them: annotate the subclass with the schema it expects, as in
    `class CreateOrder(Handler[OrderSchema])`, and `self.req.data` carries that
    type for your IDE.

    Do not override `__init__`. Heaven wll construct the instance with exactly these
    three arguments, and a subclass that changes the signature cannot be built.
    Per-request setup belongs at the top of the method.
    """

    def __init__(self, req: 'Request[T]', res: 'Response', ctx: 'Context'):
        self.req = req
        self.res = res
        self.ctx = ctx

