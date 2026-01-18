import unittest
import heaven

from msgspec import Struct
from heaven import Schema

class TestLibrary(unittest.TestCase):
    def test_version(self):
        self.assertEqual(heaven.__version__, '1.2.1')

    def test_schema_export(self):
        assert issubclass(Schema, Struct)
    
    def test_schema_field(self):
        assert Schema.Field is not None

        class User(Schema):
            name: str = Schema.Field(name='username')
        
        # msgspec Structs use __struct_fields__ which is a tuple of strings
        assert User.__struct_fields__ == ('name',)

    def test_constraints_export(self):
        from heaven import Constraints
        from msgspec import Meta
        assert Constraints is Meta

if __name__ == '__main__':
    unittest.main()
