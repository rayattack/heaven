from unittest import TestCase

from routerling.utils import b_or_s, preprocessor


class TestUtils(TestCase):
    def setUp(self) -> None:
        return super().setUp()

    def test_b_or_s(self):
        a, b = 'a str', b'a byte str'
        assert b_or_s(a) == a
        assert b_or_s(b) == 'a byte str'
