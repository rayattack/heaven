import msgspec
from msgspec import Struct, field, Meta as Constraints


class Schema(Struct):
    Field = field



from typing import Annotated

def Field(
    type_const,
    default=msgspec.NODEFAULT,
    *,
    min=None, 
    max=None,
    step=None,
    desc=None,
    example=None,
    format=None,
    error_hint=None,
    **kwargs
):
    """
    A smart helper that returns an Annotated type with msgspec constraints.
    Usage:
        age: Field(int, min=18)
        email: Field(str, format="email")
    """
    # Type Inference Helper
    is_numeric = type_const in (int, float)
    is_sequence = type_const in (str, list, dict, bytes, bytearray)
    
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
    ge = kwargs.pop("ge", None)
    le = kwargs.pop("le", None)
    min_length = kwargs.pop("min_length", None)
    max_length = kwargs.pop("max_length", None)
    multiple_of = kwargs.pop("multiple_of", step)

    if min is not None:
        if is_numeric: ge = min
        elif is_sequence: min_length = min
        else:
            if isinstance(min, float): ge = min
            else: min_length = min
            
    if max is not None:
        if is_numeric: le = max
        elif is_sequence: max_length = max
        else:
            if isinstance(max, float): le = max
            else: max_length = max

    # Filter out None
    constraints = {
        "ge": ge, "le": le, 
        "min_length": min_length, "max_length": max_length, 
        "multiple_of": multiple_of,
        "description": desc,
        "extra_json_schema": extra if extra else None
    }
    constraints.update(kwargs)
    clean_constraints = {k: v for k, v in constraints.items() if v is not None}
    
    # Return Annotated type
    return Annotated[type_const, Constraints(**clean_constraints)]
