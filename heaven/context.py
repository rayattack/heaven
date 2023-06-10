class Context():
    def __init__(self, application):
        self._application = application
        self._data = {}

    def keep(self, key, value):
        self._data[key] = value

    def __getattr__(self, key):
        return self._data.get(key)
