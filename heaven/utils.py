from datetime import date, datetime
from ipaddress import ip_address
from uuid import UUID

from .constants import DEFAULT


def boolean(value: str) -> bool:
    """Parse a boolean out of a url. Raises on anything that is not an obvious true
    or false, so a caller can tell a real False from a value it could not read."""
    try: return {'true': True, '1': True, 'false': False, '0': False}[value.strip().lower()]
    except (AttributeError, KeyError): raise ValueError(f'{value!r} is not a boolean')


# The type names usable in both `/orders/:id:int` route segments and `?id:int` query
# hints. One table so the two surfaces cannot drift apart. Every converter raises on
# input it cannot parse; what each surface does with that failure is its own choice.
CONVERTERS = {
    'bool': boolean,
    'date': date.fromisoformat,
    'datetime': datetime.fromisoformat,
    'float': float,
    'int': int,
    'str': str,
    'uuid': UUID,
}


def parameter_parts(segment: str):
    """Split a route parameter body such as `id:int` into (name, kind). The first
    colon separates the two; a segment without one is untyped."""
    name, _, kind = segment.partition(':')
    return name, kind.lower()


b_or_s = lambda x: x.decode() if isinstance(x, bytes) else x

    
def preprocessor(scope):
    headers = {}
    for header in scope.get('headers'):
        key, value = [b_or_s(e) for e in header]
        exists = headers.get(key)
        if exists:
            if isinstance(exists, list): exists.append(value)
            else: exists = [exists, value]
        else: exists = value
        headers[key] = exists

    host: bytes = headers.get('host')
    if not host: return DEFAULT, headers
    if host.startswith('http://'): host = host.replace('http://', '')
    else: host = host.replace('https://', '')
    host = host.rsplit(':')[0]
    try: ip_address(host)
    except: pass
    else: return DEFAULT, headers
    parts = host.split('.', 2)
    has_subdomain = len(parts) > 2
    return (parts[0], headers,) if has_subdomain else (DEFAULT, headers,)


class Lookup(object):
    def __init__(self, data: dict):
        self._data = data
    
    def __getattr__(self, key: str):
        value = self._data.get(key)
        if isinstance(value, dict):
            return Lookup(value)
        return value
