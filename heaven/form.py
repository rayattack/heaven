from io import BytesIO
from re import compile as _compile
from shutil import copyfileobj
from tempfile import SpooledTemporaryFile
from typing import Any, TYPE_CHECKING
from urllib.parse import parse_qs

if TYPE_CHECKING:
    from heaven.request import Request


# Ceilings on what one form may cost. FIELD_LIMIT bounds a single non-file value,
# which is the only thing streamed parsing keeps in memory; file parts above
# SPOOL_LIMIT move to a temp file on disk instead. Module-level on purpose, so an
# application that needs different ceilings can set them before serving:
# `import heaven.form; heaven.form.FIELD_LIMIT = 8 * 1024 * 1024`.
FIELD_LIMIT = 1024 * 1024
HEADERS_LIMIT = 16 * 1024
PARTS_LIMIT = 1000
SPOOL_LIMIT = 256 * 1024

_PREAMBLE, _MARGIN, _HEADERS, _DATA, _EPILOGUE = range(5)

_PARAM = _compile(r'([^=;\s]+)\s*=\s*(?:"((?:[^"\\]|\\.)*)"|([^;]*))')


def _header_params(value: str) -> dict:
    """The `key=value` parameters of a header like content-disposition or
    content-type, quotes removed. `form-data; name="a"` -> {'name': 'a'}."""
    params = {}
    for match in _PARAM.finditer(value):
        if match.group(2) is not None:
            params[match.group(1).lower()] = match.group(2).replace('\\"', '"')
        else:
            params[match.group(1).lower()] = match.group(3).strip()
    return params


def _boundary(content_type: str) -> bytes:
    boundary = _header_params(content_type).get('boundary')
    if not boundary:
        raise ValueError('multipart form has no boundary in its content-type header')
    return boundary.encode()


class MultipartParser(object):
    """Incremental multipart/form-data parser. Feed it the body in whatever pieces
    it arrives in and it returns events: ('begin', headers) opening a part,
    ('data', bytes) with a slice of that part's payload, ('end',) closing it, and
    ('finished',) at the terminating boundary. A boundary may arrive split across
    feeds; unscanned bytes that could still turn out to be one are held back until
    the next feed decides."""

    def __init__(self, boundary: bytes):
        # A delimiter is CRLF + '--' + boundary. Seeding the buffer with CRLF lets
        # the first boundary, which arrives without a preceding CRLF, match the
        # same search as every other one.
        self._delimiter = b'\r\n--' + boundary
        self._buffer = bytearray(b'\r\n')
        self._state = _PREAMBLE
        self._parts = 0

    def feed(self, chunk: bytes) -> list:
        self._buffer.extend(chunk)
        events = []
        advancing = True
        while advancing:
            if self._state == _PREAMBLE: advancing = self._skip_preamble()
            elif self._state == _MARGIN: advancing = self._cross_margin(events)
            elif self._state == _HEADERS: advancing = self._take_headers(events)
            elif self._state == _DATA: advancing = self._take_data(events)
            else:
                del self._buffer[:]
                advancing = False
        return events

    def close(self):
        if self._state != _EPILOGUE:
            raise ValueError('multipart body ended before the closing boundary')

    def _skip_preamble(self):
        index = self._buffer.find(self._delimiter)
        if index < 0:
            # keep only a tail short enough that it cannot hold a whole delimiter,
            # in case one is arriving split across this feed and the next
            keep = len(self._delimiter) - 1
            if len(self._buffer) > keep: del self._buffer[:len(self._buffer) - keep]
            return False
        del self._buffer[:index + len(self._delimiter)]
        self._state = _MARGIN
        return True

    def _cross_margin(self, events):
        """Just past a delimiter: '--' closes the body, otherwise optional padding
        then CRLF opens the next part's headers."""
        if len(self._buffer) < 2: return False
        if self._buffer[:2] == b'--':
            self._state = _EPILOGUE
            events.append(('finished',))
            return True
        index = self._buffer.find(b'\r\n', 0, 130)
        if index < 0:
            if len(self._buffer) > 128:
                raise ValueError('malformed multipart body: no line break after a boundary')
            return False
        if self._buffer[:index].strip(b' \t'):
            raise ValueError('malformed multipart body: unexpected bytes after a boundary')
        del self._buffer[:index + 2]
        self._parts += 1
        if self._parts > PARTS_LIMIT:
            raise ValueError(f'multipart body has more than {PARTS_LIMIT} parts; PARTS_LIMIT in heaven.form sets the ceiling')
        self._state = _HEADERS
        return True

    def _take_headers(self, events):
        if self._buffer[:2] == b'\r\n':
            block, consumed = b'', 2
        else:
            index = self._buffer.find(b'\r\n\r\n')
            if index < 0:
                if len(self._buffer) > HEADERS_LIMIT:
                    raise ValueError(f'multipart part headers are larger than {HEADERS_LIMIT} bytes; HEADERS_LIMIT in heaven.form sets the ceiling')
                return False
            block, consumed = bytes(self._buffer[:index]), index + 4
        del self._buffer[:consumed]

        headers = {}
        for line in block.split(b'\r\n'):
            if b':' not in line: continue
            try: text = line.decode()
            except UnicodeDecodeError: text = line.decode('latin-1')
            key, _, value = text.partition(':')
            headers[key.strip().lower()] = value.strip()
        events.append(('begin', headers))
        self._state = _DATA
        return True

    def _take_data(self, events):
        index = self._buffer.find(self._delimiter)
        if index < 0:
            # everything except a possible partial delimiter at the tail is payload
            safe = len(self._buffer) - (len(self._delimiter) - 1)
            if safe > 0:
                events.append(('data', bytes(self._buffer[:safe])))
                del self._buffer[:safe]
            return False
        if index: events.append(('data', bytes(self._buffer[:index])))
        del self._buffer[:index + len(self._delimiter)]
        events.append(('end',))
        self._state = _MARGIN
        return True


class File(object):
    def __init__(self, filename: str, content: bytes = None, content_type: str = None):
        self.filename = filename
        self.content_type = content_type
        self._content = content
        self._storage = None
        self._size = len(content) if content is not None else 0

    @property
    def content(self) -> bytes:
        """The whole file as bytes. A part that spilled to disk is read back in
        full, so for anything large prefer save() or file."""
        if self._storage is not None:
            self._storage.seek(0)
            return self._storage.read()
        return self._content

    @content.setter
    def content(self, value: bytes):
        self._content = value
        self._storage = None
        self._size = len(value) if value is not None else 0

    @property
    def file(self):
        """A binary file object positioned at the start: the spool for a streamed
        part, an in-memory reader otherwise. Hand it to anything that reads files."""
        if self._storage is not None:
            self._storage.seek(0)
            return self._storage
        return BytesIO(self._content or b'')

    @property
    def size(self) -> int:
        return self._size

    def save(self, destination) -> str:
        """Copy the upload to `destination` in chunks, never holding it whole."""
        with open(destination, 'wb') as target:
            copyfileobj(self.file, target, 64 * 1024)
        return destination


class Form(object):
    def __init__(self, req: 'Request'):
        self._data = {}
        self._loaded = not getattr(req, '_streaming', False)
        self._req = req
        self._name = None
        self._sink = None
        if self._loaded: self._parse(req)

    def __await__(self):
        return self._load().__await__()

    async def _load(self):
        """Parse the form off the live request stream. On a buffered route the form
        is parsed already and this returns immediately, so `await req.form` is safe
        everywhere."""
        if self._loaded: return self
        req = self._req
        content_type = req.headers.get('content-type', '')
        source = req.stream()
        try:
            if 'multipart/form-data' in content_type:
                parser = MultipartParser(_boundary(content_type))
                fed = False
                async for chunk in source:
                    fed = True
                    for event in parser.feed(chunk): self._absorb(event)
                if fed: parser.close()
            else:
                collected, size = [], 0
                async for chunk in source:
                    size += len(chunk)
                    if size > FIELD_LIMIT:
                        raise ValueError(f'urlencoded form is larger than {FIELD_LIMIT} bytes; FIELD_LIMIT in heaven.form sets the ceiling')
                    collected.append(chunk)
                body = b''.join(collected)
                try: body = body.decode()
                except UnicodeDecodeError: body = body.decode('latin-1')
                self._absorb_urlencoded(body)
        except ValueError:
            # The rest of the body is read and dropped so the client gets to finish
            # sending and actually receive the error response. Answering mid-upload
            # resets the connection instead, same reasoning as Routes.buffer.
            async for _ in source: pass
            raise
        self._loaded = True
        return self

    def _parse(self, req: 'Request'):
        content_type = req.headers.get('content-type', '')
        if 'multipart/form-data' in content_type:
            self._parse_multipart(req, content_type)
        elif 'application/x-www-form-urlencoded' in content_type:
            self._parse_urlencoded(req)

    def _parse_multipart(self, req: 'Request', content_type: str):
        body = req.body
        if not body: return
        parser = MultipartParser(_boundary(content_type))
        # fed in slices so the parser's working set stays small and a large file
        # part spills to its temp file instead of sitting in memory a second time
        for start in range(0, len(body), 65536):
            for event in parser.feed(body[start:start + 65536]): self._absorb(event)
        parser.close()

    def _parse_urlencoded(self, req: 'Request'):
        body = req.body.decode() if isinstance(req.body, bytes) else req.body
        self._absorb_urlencoded(body)

    def _absorb_urlencoded(self, body: str):
        parsed = parse_qs(body)
        for key, values in parsed.items():
            for value in values:
                self._add_to_data(key, value)

    def _absorb(self, event):
        kind = event[0]
        if kind == 'begin':
            headers = event[1]
            params = _header_params(headers.get('content-disposition', ''))
            name, filename = params.get('name'), params.get('filename')
            self._name = name
            if not name: self._sink = None
            elif filename:
                self._sink = File(filename, content_type=headers.get('content-type'))
                self._sink._storage = SpooledTemporaryFile(max_size=SPOOL_LIMIT)
            else: self._sink = bytearray()
        elif kind == 'data':
            sink = self._sink
            if sink is None: return
            data = event[1]
            if isinstance(sink, File):
                sink._storage.write(data)
                sink._size += len(data)
            else:
                if len(sink) + len(data) > FIELD_LIMIT:
                    raise ValueError(f'form field {self._name} is larger than {FIELD_LIMIT} bytes; FIELD_LIMIT in heaven.form sets the ceiling')
                sink.extend(data)
        elif kind == 'end':
            name, sink = self._name, self._sink
            self._name = self._sink = None
            if sink is None: return
            if isinstance(sink, File):
                sink._storage.seek(0)
                self._add_to_data(name, sink)
            else:
                value = bytes(sink)
                try: value = value.decode()
                except: pass
                self._add_to_data(name, value)

    def _add_to_data(self, key: str, value: Any):
        if key in self._data:
            if isinstance(self._data[key], list):
                self._data[key].append(value)
            else:
                self._data[key] = [self._data[key], value]
        else:
            self._data[key] = value

    def _guard(self):
        if not self.__dict__.get('_loaded'):
            raise RuntimeError(
                'This route was registered with stream=True so its form has not been '
                'parsed yet. Await it first: `form = await req.form`.'
            )

    def __getattr__(self, name: str) -> Any:
        self._guard()
        return self._data.get(name)

    def get(self, name: str, default: Any = None) -> Any:
        self._guard()
        return self._data.get(name, default)

    def to_dict(self) -> dict:
        self._guard()
        return self._data
