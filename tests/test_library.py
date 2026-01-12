import unittest
import heaven
from msgspec import Struct

class TestLibrary(unittest.TestCase):
    def test_version(self):
        self.assertEqual(heaven.__version__, '0.6.7')

    def test_schema_export(self):
        from heaven import Schema
        self.assertIs(Schema, Struct)

if __name__ == '__main__':
    unittest.main()
