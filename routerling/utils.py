from ipaddress import ip_address

from .constants import DEFAULT

    
def preprocessor(self, scope):
    headers = {}

    for header in scope.get('headers'):
        key, value = header
        headers[key.decode()] = value.decode()

    host: bytes = headers.get('host')
    if host.startswith('http://'): host = host.replace('http://', '')
    else: host = host.replace('https://', '')
    host = host.rsplit(':')[0]
    try: ip_address(host)
    except: pass
    else: return DEFAULT, headers
    parts = host.split('.', 2)
    has_subdomain = len(parts) > 2
    return (parts[0], headers,) if has_subdomain else (DEFAULT, headers,)
