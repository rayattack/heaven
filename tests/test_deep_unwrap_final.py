import inspect
from functools import wraps, partial
import os
from typing import Any

from heaven.cli import _deep_unwrap


def auth(role: str):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            return f(*args, **kwargs)
        return wrapper
    return decorator

@auth("admin")
def protected_handler():
    """This is the original handler."""
    pass

def test_final_fix():
    handler = protected_handler
    original = _deep_unwrap(handler)
    
    print(f"Name: {getattr(original, '__name__', 'N/A')}")
    print(f"File: {os.path.basename(inspect.getsourcefile(original))}")
    print(f"Line: {inspect.getsourcelines(original)[1]}")
    
    assert original.__name__ == "protected_handler"
    assert "protected_handler" in inspect.getsource(original)

if __name__ == "__main__":
    test_final_fix()
