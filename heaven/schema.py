import msgspec
from msgspec import Struct, field, Meta as Constraints


class Schema(Struct):
    Field = field



def Field(
    default=msgspec.NODEFAULT,
    *,
    min=None, 
    max=None,
    min_len=None,
    max_len=None,
    step=None,
    desc=None,
    example=None,
    format=None,
    error_hint=None,
    **kwargs
) -> Constraints:
    """
    A smart helper for defining msgspec.Meta constraints.
    Returns `msgspec.Meta` (Constraints) for use with `Annotated`.
    
    Usage:
        age: Annotated[int, Field(min=18)]      # Numeric: min -> ge
        slug: Annotated[str, Field(min_len=3)]  # String: min_len -> min_length
    """
    # Pre-defined Patterns
    if format == "email":
        kwargs["pattern"] = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    elif format == "uuid":
        kwargs["pattern"] = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
    elif format == "slug":
        kwargs["pattern"] = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"

    # Metadata
    extra = kwargs.pop("extra_json_schema", {}) or {}
    if example: extra["example"] = example
    if format: extra["format"] = format
    if error_hint: extra["error_hint"] = error_hint

    # Constraint Mapping
    # min/max -> ge/le (Value)
    ge = kwargs.pop("ge", min)
    le = kwargs.pop("le", max)
    
    # min_len/max_len -> min_length/max_length (Length)
    # We check both the shortened alias and the raw msgspec kwarg
    min_length = kwargs.pop("min_length", min_len)
    max_length = kwargs.pop("max_length", max_len)
    
    multiple_of = kwargs.pop("multiple_of", step)

    # Clean up
    constraints = {
        "ge": ge, "le": le, 
        "min_length": min_length, "max_length": max_length, 
        "multiple_of": multiple_of,
        "description": desc,
        "extra_json_schema": extra if extra else None
    }
    constraints.update(kwargs)
    clean_constraints = {k: v for k, v in constraints.items() if v is not None}
    
    # Return Constraints (Meta) directly
    return Constraints(**clean_constraints)
