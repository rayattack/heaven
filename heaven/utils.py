from ipaddress import ip_address

from .constants import DEFAULT


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
