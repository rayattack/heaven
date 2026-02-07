
import unittest
import msgspec
from typing import Annotated, Union
from heaven import Field, Constraints

class TestSchemaField(unittest.TestCase):
    def test_numeric_bounds(self):
        """Test that min/max map to ge/le"""
        f = Field(min=10, max=20)
        self.assertEqual(f.ge, 10)
        self.assertEqual(f.le, 20)
        self.assertIsNone(f.min_length)
        self.assertIsNone(f.max_length)

    def test_sequence_length(self):
        """Test that min_len/max_len map to min_length/max_length"""
        # Strings
        f = Field(min_len=3, max_len=50)
        self.assertEqual(f.min_length, 3)
        self.assertEqual(f.max_length, 50)
        self.assertIsNone(f.ge) # Ensure no numeric constraints mixed in

        # Arrays/Lists (same logic in msgspec)
        f_list = Field(min_len=1)
        self.assertEqual(f_list.min_length, 1)

    def test_formats(self):
        """Test pre-baked formats"""
        # Email
        f_email = Field(format="email")
        f_email = Field(format="email")
        # Pattern is a first-class citizen in msgspec.Meta
        self.assertIsNotNone(f_email.pattern)
        self.assertIn("@", f_email.pattern)
        
        # UUID
        f_uuid = Field(format="uuid")
        self.assertIsNotNone(f_uuid.pattern)

        # Slug
        f_slug = Field(format="slug")
        self.assertEqual(f_slug.pattern, r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

    def test_mixed_constraints(self):
        """Test passing both numeric and length (e.g. intentionally or via kwargs)"""
        # Users shouldn't do this for one field, but `Field` shouldn't crash if valid kwargs passed.
        # But msgspec.Meta might crash if incompatible?
        # Let's test standard usage.
        pass

    def test_metadata(self):
        """Test description, examples, error_hint"""
        f = Field(desc="A test field", example="foo", error_hint="Bad input")
        self.assertEqual(f.description, "A test field")
        self.assertEqual(f.extra_json_schema["example"], "foo")
        self.assertEqual(f.extra_json_schema["error_hint"], "Bad input")

    def test_step(self):
        """Test step maps to multiple_of"""
        f = Field(step=5)
        self.assertEqual(f.multiple_of, 5)

    def test_escape_hatch(self):
        """Test the 10% usage: passing raw native Constraints via kwargs"""
        # Test mixing mapped args (min_len) with native kwargs (pattern)
        # This is a valid String constraint combo.
        f = Field(min_len=5, pattern="^a")
        
        # Check standard mapping
        self.assertEqual(f.min_length, 5)
        
        # Check passthrough
        self.assertEqual(f.pattern, "^a")

        # What if user passes garbage?
        # msgspec.Meta is strict, so we expect a TypeError
        with self.assertRaises(TypeError):
            Field(garbage="trash")


class TestEndToEndValidation(unittest.TestCase):
    """
    Verify that Field() actually works when used in a real msgspec.Struct.
    This tests the "10% advanced" use cases: Unions, Timezones, etc.
    """
    def test_timezone_constraint(self):
        """Test native msgspec 'tz' constraint (passed via kwargs)"""
        from datetime import datetime, timezone
        
        class TimeModel(msgspec.Struct):
            # 'tz=True' requires timezone-aware input
            dt: Annotated[datetime, Field(tz=True)]

        # Valid (Aware)
        valid_json = b'{"dt": "2023-01-01T12:00:00Z"}'
        obj = msgspec.json.decode(valid_json, type=TimeModel)
        self.assertIsNotNone(obj.dt.tzinfo)

        # Invalid (Naive) - msgspec should reject
        invalid_json = b'{"dt": "2023-01-01T12:00:00"}'
        with self.assertRaises(msgspec.ValidationError):
            msgspec.json.decode(invalid_json, type=TimeModel)

    def test_advanced_union_constraints(self):
        """Test Field() used within Unions (Deep msgspec territory)"""
        # Scenario: ID can be an Integer (>= 1) OR a UUID String
        # We must wrap the INT with the Constraint, not the whole Union?
        # msgspec supports Annotated inside Union.
        
        class IDModel(msgspec.Struct):
            # Complex: Union of (Int >= 1) | (String UUID)
            # Note: We use Field() for the Int constraint
            id: int | str

            # Option A: Constrained Int | String
            u1: Annotated[int, Field(min=1)] | str
            
            # Option B: Constrained Int | Constrained String (UUID format)
            u2: Annotated[int, Field(min=1)] | Annotated[str, Field(format="uuid")]

        # Test u1: Int < 1 should fail if it matches int generic? 
        # Actually msgspec tries to match types. 
        # If input is 0, it matches `int`. Constraint(ge=1) fails. 
        # Does it fall back to `str`? No, 0 is not a string.
        
        # Valid Int
        obj = msgspec.json.decode(b'{"id": 1, "u1": 10, "u2": 10}', type=IDModel)
        self.assertEqual(obj.u1, 10)

        # Invalid Int (0) for u1
        # Should raise ValidationError because 0 matches int but fails ge=1, and isn't a string.
        with self.assertRaises(msgspec.ValidationError):
            msgspec.json.decode(b'{"id": 1, "u1": 0, "u2": "uuid"}', type=IDModel)
            
        # Valid ID (UUID string) for u2
        uuid_str = "123e4567-e89b-12d3-a456-426614174000"
        obj = msgspec.json.decode(f'{{"id": 1, "u1": 1, "u2": "{uuid_str}"}}'.encode(), type=IDModel)
        self.assertEqual(obj.u2, uuid_str)

        # Invalid UUID format for u2
        with self.assertRaises(msgspec.ValidationError):
            msgspec.json.decode(b'{"id": 1, "u1": 1, "u2": "not-a-uuid"}', type=IDModel)

    def test_array_constraints(self):
        """Test min_len on Lists"""
        class TagModel(msgspec.Struct):
            # List must have at least 2 items
            tags: Annotated[list[str], Field(min_len=2)]
            
            # ITEMS in list must be min_len=3
            names: list[Annotated[str, Field(min_len=3)]]

        # Valid
        msgspec.json.decode(b'{"tags": ["a", "b"], "names": ["bob", "tim"]}', type=TagModel)

        # Invalid List Length (< 2)
        with self.assertRaises(msgspec.ValidationError):
            msgspec.json.decode(b'{"tags": ["a"], "names": ["bob"]}', type=TagModel)
            
        # Invalid Item Length (< 3)
        with self.assertRaises(msgspec.ValidationError):
            msgspec.json.decode(b'{"tags": ["a", "b"], "names": ["bo"]}', type=TagModel)

if __name__ == "__main__":
    unittest.main()
