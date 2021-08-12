from unittest import TestCase

from routerling import Context


class TestContext(TestCase):
    def setUp(self) -> None:
        self.context = Context()
        return super().setUp()
    
    def test_keep(self):
        self.context.keep('something', 5)
        self.assertEqual(self.context.something, 5)
