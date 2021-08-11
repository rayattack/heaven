from unittest import TestCase

from routerling import HttpRequest, ResponseWriter, Context


mock_scope = {}
mock_receive = {}
mock_metadata = {}


def one(r: HttpRequest, w: ResponseWriter, c: Context):
    """Response should be tested in response class but setup of body done here"""
    w.body = 1000

def two(r: HttpRequest, w: ResponseWriter, c: Context):
    w.body = 2000

def three(r: HttpRequest, w: ResponseWriter, c: Context):
    w.body = 3000

def four(r: HttpRequest, w: ResponseWriter, c: Context):
    w.body = 4000


class TestRequest(TestCase):
    pass
