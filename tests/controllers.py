"""
Handler classes for string disco tests. They live in their own module 
cos `'package.module.Class#method'` has to resolve via a real import.
"""

from asyncio import Event
from typing import Annotated, TypedDict

from heaven import Handler


class Order(TypedDict):
    reference: Annotated[str, 'min_len=3']


class Orders(Handler):
    async def index(self):
        """List the orders."""
        self.res.body = {'route': self.req.route, 'who': self.ctx.who}

    def show(self):
        self.res.body = f'order {self.req.params.get("id")}'

    async def create(self: 'Handler[Order]'):
        self.res.body = self.req.data

    async def upload(self):
        total = 0
        async for chunk in self.req.stream(): total += len(chunk)
        self.res.body = str(total).encode()

    not_a_method = 'just an attribute'


class Typed(Handler[Order]):
    async def create(self):
        self.res.body = self.req.data


class Guard(Handler):
    async def before(self):
        self.ctx.who = 'guarded'


class Interleaved(Handler):
    """Two requests are held in flight at the same time, so a shared instance
    would show up as one request seeing the other's state."""
    first = Event()
    second = Event()
    seen = []

    @classmethod
    def reset(cls):
        cls.first, cls.second, cls.seen = Event(), Event(), []

    async def slow(self):
        self.tag = self.req.queries.get('n')
        Interleaved.seen.append(id(self))
        if self.tag == '1':
            Interleaved.first.set()
            await Interleaved.second.wait()
        else:
            await Interleaved.first.wait()
            Interleaved.second.set()
        # a shared instance would have had self.tag overwritten by the other request
        self.res.body = self.tag


class NotAHandler(object):
    async def index(self): pass


def plain(req, res, ctx):
    """A function handler, to prove the older string form still works."""
    res.body = b'plain'


