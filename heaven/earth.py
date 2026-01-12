from asyncio import run
from typing import Union

from heaven.context import Context
from heaven.response import Response
from heaven.router import App
from heaven.request import Request


class Session(object):
    def __init__(self, headers, params, body):
        pass

    def refresh(self):
        pass


class Earth(object):
    def __init__(self, heaven: App):
        self.__app = heaven
        self.__sessions = {
            "*": Session(headers = None, params = None, body = None)
        }  # here we use keys to save headers etc for reuse

    async def receive(self):
        pass

    def ON(self, middleware: str, replacement: str):
        """
        Replace middlewares you don't want to run otherwise your handlers
        will be invoked with actual middleware definitions.

        Alternatively use custom environmentalal variables to point to new environments.
        """
        pass

    async def send(self):
        pass

    def scope():
        return {}

    @property
    def heaven(self) -> App:
        return self.__app

    def GET(self, endpoint: str, session: Union[str, Session] = None) -> tuple[Request, Response, Context]:
        if isinstance(session, str):
            session = self.__sessions.get(session or '*')
        # write code to simulate GET request to endpoint specified by endpoint and
        # return the trinity of req, res, ctx so you can assert different things with them
        async def runner():
            await self.__app(self.scope(), self.receive(), self.send())
        run(runner())
        req = Request(scope = {}, body = None, receive = None, application = self.__app)
        ctx = Context(self.__app)
        res = Response(self.__app, ctx, req)
        return req, res, ctx
    
    def POST(self, endpoint: str, body = None, session: Sessionable) -> Trinity:
        return req, res, ctx

