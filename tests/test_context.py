from unittest import TestCase

from routerling import Context, Router


router = Router()


class TestContext(TestCase):
    def setUp(self) -> None:
        self.context = Context(router)
        return super().setUp()

    def test_keep(self):
        self.context.keep('something', 5)
        self.assertEqual(self.context.something, 5)
