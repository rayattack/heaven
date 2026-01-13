from typing import Any


class Context():
    def __init__(self, application):
        self._application = application
        self._data = {}

    def keep(self, key, value):
        self._data[key] = value

    def peek(self, key):
        return self._data.get(key)

    def unkeep(self, key):
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
