from typing import Any


class Context():
    def __init__(self, application):
        self._application = application
        self._data = {}

    def keep(self, key, value):
        self._data[key] = value

    def __getattr__(self, key):
        return self._data.get(key)


class Look(object):
    def __init__(self, data: dict):
        self._data = data

    def __getattr__(self, key: str):
        value = self._data.get(key)
        if isinstance(value, dict):
            return Look(value)
        return value

    def __setattr__(self, __name: str, __value: Any) -> None:
        if __name == '_data': super().__setattr__(__name, __value)
        else: self._data[__name] = __value
