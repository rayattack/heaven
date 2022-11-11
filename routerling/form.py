from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from routerling.request import HttpRequest


ST = b'--'
NL = b'\r\n'


def _reqparser(req) -> dict:
    data = {}
    body = req.body
    ct = req.headers.get('content-type')
    stopper = ct.split('boundary=')[-1]
    stopped = body.split(stopper.encode())
    portions = [p.strip(NL).strip(ST).strip(NL) for p in stopped]
    for portion in portions:
        if portion == b'': continue
        prepart, _, postpart = portion.partition(NL * 2)
        key = _keyxtractor(prepart)
        data[key.decode()] = postpart
    return data


def _keyxtractor(s) -> str:
    for portion in s.split(b';'):
        name = portion.split(b'=')
        if name[0].strip(b' ') == b'name': return name[-1].strip(b'"')


class Form(object):
    def __init__(self, req: 'HttpRequest'):
        self._data = _reqparser(req)

    def __getattr__(self, name: str) -> Any:
        return self._data.get(name)
