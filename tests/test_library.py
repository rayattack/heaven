import unittest
import heaven


class TestLibrary(unittest.TestCase):
    def test_version(self):
        self.assertEqual(heaven.__version__, '1.3.8')

    def test_schema_export(self):
        from pytastic import Pytastic
        assert heaven.Pytastic is Pytastic
    
    def test_exceptions_export(self):
        from pytastic.exceptions import PytasticError, ValidationError
        assert heaven.PytasticError is PytasticError
        assert heaven.ValidationError is ValidationError

if __name__ == '__main__':
    unittest.main()
