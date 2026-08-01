from unittest import TestCase

from heaven import Context, Router
from heaven.context import Look


router = Router()


class TestContext(TestCase):
    def setUp(self) -> None:
        self.context = Context(router)
        return super().setUp()

    def test_keep(self):
        self.context.keep('something', 5)
        self.assertEqual(self.context.something, 5)

    def test_typed_key(self):
        from heaven.context import Key
        k = Key[int]("count")
        self.context.keep(k, 10)
        self.assertEqual(self.context.peek(k), 10)
        self.assertEqual(self.context.unkeep(k), 10)
        self.assertIsNone(self.context.peek(k))


class TestLook(TestCase):
    def setUp(self) -> None:
        self.look = Look({})
    
    def test_look(self):
        self.look.name = 'a'
        self.assertEqual(self.look._data, {'name': 'a'})
    
    def test_nested_lookup(self):
        self.look.nested = {'time': {'when': {'we': {'go': {'very': {'deep': 'boink'}}}}}}
        self.assertEqual(self.look.nested.time.when.we.go.very.deep, 'boink')
