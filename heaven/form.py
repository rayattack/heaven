from email.parser import BytesParser
from email.policy import default
from typing import Any, TYPE_CHECKING
from urllib.parse import parse_qs

if TYPE_CHECKING:
    from heaven.request import Request


class File(object):
    def __init__(self, filename: str, content: bytes):
        self.filename = filename
        self.content = content

class Form(object):
    def __init__(self, req: 'Request'):
        self._data = {}
        self._parse(req)

    def _parse(self, req: 'Request'):
        content_type = req.headers.get('content-type', '')
        if 'multipart/form-data' in content_type:
            self._parse_multipart(req, content_type)
        elif 'application/x-www-form-urlencoded' in content_type:
            self._parse_urlencoded(req)

    def _parse_multipart(self, req: 'Request', content_type: str):
        # email.parser expects the headers to be part of the bytes
        body = req.body
        # Ensure we have a leading boundary if it's missing or if we need to prep for parser
        # Actually BytesParser handles it if we provide the Content-Type header
        headers = f"Content-Type: {content_type}\r\n\r\n".encode()
        msg = BytesParser(policy=default).parsebytes(headers + body)
        
        if msg.is_multipart():
            for part in msg.get_payload():
                name = part.get_param('name', header='content-disposition')
                if name:
                    filename = part.get_filename()
                    value = part.get_payload(decode=True)
                    if filename:
                        value = File(filename, value)
                    else:
                        try: value = value.decode()
                        except: pass
                    self._add_to_data(name, value)

    def _parse_urlencoded(self, req: 'Request'):
        body = req.body.decode() if isinstance(req.body, bytes) else req.body
        parsed = parse_qs(body)
        for key, values in parsed.items():
            for value in values:
                self._add_to_data(key, value)

    def _add_to_data(self, key: str, value: Any):
        if key in self._data:
            if isinstance(self._data[key], list):
                self._data[key].append(value)
            else:
                self._data[key] = [self._data[key], value]
        else:
            self._data[key] = value

    def __getattr__(self, name: str) -> Any:
        return self._data.get(name)

    def get(self, name: str, default: Any = None) -> Any:
        return self._data.get(name, default)

    def to_dict(self) -> dict:
        return self._data
