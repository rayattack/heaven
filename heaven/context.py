from typing import Any, Generic, TypeVar, overload, Union

T = TypeVar("T")

class Key(Generic[T]):
    """A typed key for storing and retrieving values from the context."""
    def __init__(self, name: str):
        self.name = name

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        if isinstance(other, Key):
            return self.name == other.name
        return self.name == other

    def __str__(self):
        return self.name


class Context():
    def __init__(self, application):
        self._application = application
        self._data = {}

    @overload
    def keep(self, key: Key[T], value: T) -> None: ...
    
    @overload
    def keep(self, key: str, value: Any) -> None: ...

    def keep(self, key: Union[str, Key[T]], value: Any):
        if isinstance(key, Key):
            self._data[key.name] = value
        else:
            self._data[key] = value

    @overload
    def peek(self, key: Key[T]) -> Union[T, None]: ...
    
    @overload
    def peek(self, key: str) -> Any: ...

    def peek(self, key: Union[str, Key[T]]) -> Any:
        if isinstance(key, Key):
            return self._data.get(key.name)
        return self._data.get(key)

    def unkeep(self, key: Union[str, Key[T]]):
        if isinstance(key, Key):
            return self._data.pop(key.name, None)
        return self._data.pop(key, None)

    __reserved = {'session', 'app', 'request', 'response', 'headers', 'cookies'}

    def __getattr__(self, key) -> Any:
        return self._data.get(key)
    
    def __setattr__(self, key: str, value: Any) -> None:
        if key in self.__reserved:
            raise AttributeError(f"Cannot overwrite reserved context key: '{key}'")
        
        if key.startswith('_'):
            super().__setattr__(key, value)
        else:
            self._data[key] = value


class Look(object):
    def __init__(self, data: dict):
        self._data = data

    def __getattr__(self, key: str) -> Any:
        value = self._data.get(key)
        if isinstance(value, dict):
            return Look(value)
        return value

    def __setattr__(self, __name: str, __value: Any) -> None:
        if __name == '_data': super().__setattr__(__name, __value)
        else: self._data[__name] = __value
