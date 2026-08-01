"""Regression cover for defects fixed in 2.0.0.

Each test here pins behaviour that was previously wrong. They drive the real ASGI
entrypoint rather than Earth, because some of the behaviour (HEAD bodies, the error
page) only exists in Router.__call__.
"""
import asyncio
import inspect
import os
import shutil
import tempfile
import tracemalloc
from datetime import date, datetime
from typing import TypedDict
from unittest import IsolatedAsyncioTestCase
from uuid import UUID

from orjson import loads

from heaven import App
from heaven.errors import HandlerError, UrlError
from heaven.form import File
from heaven.request import Request
from tests import controllers


def _scope(method, path, query=b''):
    return {
        'type': 'http', 'method': method, 'path': path, 'raw_path': path.encode(),
        'query_string': query, 'headers': [(b'host', b'localhost')],
        'client': ('127.0.0.1', 8080), 'scheme': 'http',
    }


async def drive(app, method, path, body=b'', query=b''):
    """Run one request through the ASGI entrypoint, returning (status, headers, body)."""
    sent = []

    async def receive():
        return {'type': 'http.request', 'body': body, 'more_body': False}

    async def send(message):
        sent.append(message)

    await app(_scope(method, path, query), receive, send)

    status, headers, chunks = None, {}, []
    for message in sent:
        if message['type'] == 'http.response.start':
            status = message['status']
            headers = {k.decode().lower(): v.decode() for k, v in message['headers']}
        elif message['type'] == 'http.response.body':
            chunks.append(message.get('body', b''))
    return status, headers, b''.join(chunks)


def noop(req, res, ctx): pass


class AssetContainmentTest(IsolatedAsyncioTestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        os.mkdir(os.path.join(self.root, 'assets'))
        os.mkdir(os.path.join(self.root, 'assets', 'nested'))
        with open(os.path.join(self.root, 'assets', 'ok.txt'), 'w') as f:
            f.write('served')
        with open(os.path.join(self.root, 'assets', 'nested', 'deep.txt'), 'w') as f:
            f.write('deep')
        with open(os.path.join(self.root, 'private.txt'), 'w') as f:
            f.write('not yours')
        self.app = App()
        self.app.ASSETS('assets', relative_to=os.path.join(self.root, 'app.py'))

    def tearDown(self):
        shutil.rmtree(self.root)

    async def test_serves_files_inside_the_folder(self):
        status, _, body = await drive(self.app, 'GET', '/assets/ok.txt')
        self.assertEqual(status, 200)
        self.assertEqual(body, b'served')

    async def test_serves_nested_files(self):
        status, _, body = await drive(self.app, 'GET', '/assets/nested/deep.txt')
        self.assertEqual(status, 200)
        self.assertEqual(body, b'deep')

    async def test_dot_segments_do_not_escape_the_folder(self):
        status, _, _ = await drive(self.app, 'GET', '/assets/../private.txt')
        self.assertEqual(status, 404)

    async def test_repeated_dot_segments_do_not_escape_the_folder(self):
        status, _, _ = await drive(self.app, 'GET', '/assets/../../../../../../etc/passwd')
        self.assertEqual(status, 404)

    async def test_dot_segments_within_the_folder_still_resolve(self):
        status, _, body = await drive(self.app, 'GET', '/assets/nested/../ok.txt')
        self.assertEqual(status, 200)
        self.assertEqual(body, b'served')


class ResponseFileWithinTest(IsolatedAsyncioTestCase):
    """res.file(within=...) confines a read to one directory, anywhere on the
    filesystem rather than only inside the project."""

    def setUp(self):
        self.media = tempfile.mkdtemp(prefix='media-')
        self.secret = tempfile.mkdtemp(prefix='secret-')
        os.mkdir(os.path.join(self.media, 'clips'))
        with open(os.path.join(self.media, 'a.txt'), 'w') as f:
            f.write('media-a')
        with open(os.path.join(self.media, 'clips', 'b.txt'), 'w') as f:
            f.write('media-b')
        with open(os.path.join(self.secret, 's.txt'), 'w') as f:
            f.write('secret')
        os.symlink(os.path.join(self.secret, 's.txt'), os.path.join(self.media, 'out.txt'))

        self.app = App()
        media = self.media
        self.app.GET('/rel/*', lambda q, s, c: s.file(q.params.get('*', ''), within=media))
        self.app.GET('/abs/*', lambda q, s, c: s.file(
            os.path.join(media, q.params.get('*', '')), within=media))
        self.app.GET('/raw/*', lambda q, s, c: s.file(
            os.path.join(media, q.params.get('*', ''))))

    def tearDown(self):
        shutil.rmtree(self.media)
        shutil.rmtree(self.secret)

    async def test_serves_from_a_root_outside_the_project(self):
        status, _, body = await drive(self.app, 'GET', '/rel/a.txt')
        self.assertEqual(status, 200)
        self.assertEqual(body, b'media-a')

    async def test_serves_nested_paths_relative_to_the_root(self):
        status, _, body = await drive(self.app, 'GET', '/rel/clips/b.txt')
        self.assertEqual(status, 200)
        self.assertEqual(body, b'media-b')

    async def test_accepts_a_caller_built_absolute_path_under_the_root(self):
        status, _, body = await drive(self.app, 'GET', '/abs/a.txt')
        self.assertEqual(status, 200)
        self.assertEqual(body, b'media-a')

    async def test_dot_segments_staying_inside_still_resolve(self):
        status, _, body = await drive(self.app, 'GET', '/rel/clips/../a.txt')
        self.assertEqual(status, 200)
        self.assertEqual(body, b'media-a')

    async def test_paths_escaping_the_root_are_rejected(self):
        for path_ in ('/rel/../../../../etc/passwd', '/abs/../../../etc/passwd'):
            status, _, _ = await drive(self.app, 'GET', path_)
            self.assertEqual(status, 404, path_)

    async def test_symlinks_leaving_the_root_are_rejected(self):
        status, _, _ = await drive(self.app, 'GET', '/rel/out.txt')
        self.assertEqual(status, 404)

    async def test_a_relative_root_resolves_against_the_working_directory(self):
        app = App()
        app.GET('/p/*', lambda q, s, c: s.file(q.params.get('*', ''), within='tests'))
        status, _, body = await drive(app, 'GET', '/p/test_library.py')
        self.assertEqual(status, 200)
        self.assertIn(b'import heaven', body)
        status, _, _ = await drive(app, 'GET', '/p/../pyproject.toml')
        self.assertEqual(status, 404)

    async def test_without_within_the_primitive_is_unconfined(self):
        status, _, body = await drive(self.app, 'GET', '/raw/a.txt')
        self.assertEqual(status, 200)
        self.assertEqual(body, b'media-a')


class ErrorPageDefaultTest(IsolatedAsyncioTestCase):
    @staticmethod
    def _explode(req, res, ctx):
        raise RuntimeError('connection string 12345')

    async def test_debug_is_off_by_default(self):
        app = App()
        app.GET('/boom', self._explode)
        status, _, body = await drive(app, 'GET', '/boom')
        self.assertEqual(status, 500)
        self.assertEqual(body, b'Internal Server Error')
        self.assertNotIn(b'12345', body)

    async def test_debug_can_still_be_opted_into(self):
        app = App(debug=True)
        app.GET('/boom', self._explode)
        status, _, body = await drive(app, 'GET', '/boom')
        self.assertEqual(status, 500)
        self.assertIn(b'12345', body)


class PrefixRouteTest(IsolatedAsyncioTestCase):
    """A url that is a strict prefix of a registered route used to raise."""

    async def test_prefix_of_registered_route_is_a_miss(self):
        app = App()
        app.GET('/a/b/c', noop)
        for path in ('/a/b', '/a'):
            status, _, _ = await drive(app, 'GET', path)
            self.assertEqual(status, 404, path)

    async def test_prefix_through_a_parameter_is_a_miss(self):
        app = App()
        app.GET('/users/:id/orders', noop)
        status, _, _ = await drive(app, 'GET', '/users/5')
        self.assertEqual(status, 404)

    async def test_registered_route_still_matches(self):
        app = App()
        app.GET('/a/b/c', noop)
        status, _, _ = await drive(app, 'GET', '/a/b/c')
        self.assertEqual(status, 200)

    async def test_wildcard_still_absorbs_the_prefix(self):
        app = App()
        app.GET('/a/b/c', noop)
        app.GET('/*', noop)
        status, _, _ = await drive(app, 'GET', '/a/b')
        self.assertEqual(status, 200)


class HookOrderTest(IsolatedAsyncioTestCase):
    async def test_before_runs_broadest_first_and_after_mirrors_it(self):
        order = []
        app = App()
        app.BEFORE('/users/:id', lambda q, s, c: order.append('B:exact'))
        app.BEFORE('/*', lambda q, s, c: order.append('B:/*'))
        app.BEFORE('/users/*', lambda q, s, c: order.append('B:/users/*'))
        app.AFTER('/users/:id', lambda q, s, c: order.append('A:exact'))
        app.AFTER('/*', lambda q, s, c: order.append('A:/*'))
        app.AFTER('/users/*', lambda q, s, c: order.append('A:/users/*'))
        app.GET('/users/:id', lambda q, s, c: order.append('HANDLER'))

        await drive(app, 'GET', '/users/7')

        self.assertEqual(order, [
            'B:/*', 'B:/users/*', 'B:exact',
            'HANDLER',
            'A:exact', 'A:/users/*', 'A:/*',
        ])

    async def test_a_hook_matching_several_patterns_runs_once(self):
        calls = []
        def hook(q, s, c): calls.append(1)
        app = App()
        app.BEFORE('/*', hook)
        app.BEFORE('/x', hook)
        app.GET('/x', noop)
        await drive(app, 'GET', '/x')
        self.assertEqual(len(calls), 1)


class HookMethodScopeTest(IsolatedAsyncioTestCase):
    async def test_scope_does_not_leak_to_another_registration(self):
        fired = []
        def shared(q, s, c): fired.append(q.url)

        scoped = App()
        scoped.BEFORE('/admin', shared, methods=['POST'])
        scoped.GET('/admin', noop)

        unscoped = App()
        unscoped.BEFORE('/public', shared)
        unscoped.GET('/public', noop)

        await drive(unscoped, 'GET', '/public')
        self.assertEqual(fired, ['/public'])

    async def test_scope_is_honoured(self):
        fired = []
        def guard(q, s, c): fired.append(q.method)
        app = App()
        app.BEFORE('/admin', guard, methods=['POST'])
        app.GET('/admin', noop)
        app.POST('/admin', noop)

        await drive(app, 'GET', '/admin')
        self.assertEqual(fired, [])
        await drive(app, 'POST', '/admin')
        self.assertEqual(fired, ['POST'])

    async def test_no_attribute_is_written_onto_the_handler(self):
        def guard(q, s, c): pass
        app = App()
        app.BEFORE('/admin', guard, methods=['POST'])
        self.assertFalse(hasattr(guard, '_hook_methods'))

    async def test_bound_methods_can_be_scoped(self):
        fired = []

        class Plugin:
            def guard(self, req, res, ctx): fired.append(req.method)

        app = App()
        app.BEFORE('/z', Plugin().guard, methods=['POST'])
        app.POST('/z', noop)
        await drive(app, 'POST', '/z')
        self.assertEqual(fired, ['POST'])


class MethodNotAllowedTest(IsolatedAsyncioTestCase):
    async def test_method_mismatch_is_405_with_allow(self):
        app = App()
        app.GET('/g', noop)
        app.PUT('/g', noop)
        status, headers, _ = await drive(app, 'POST', '/g')
        self.assertEqual(status, 405)
        self.assertEqual(headers.get('allow'), 'GET, HEAD, PUT')

    async def test_unknown_path_is_still_404(self):
        app = App()
        app.GET('/g', noop)
        status, _, _ = await drive(app, 'GET', '/nowhere')
        self.assertEqual(status, 404)

    async def test_405_resolves_through_parameters(self):
        app = App()
        app.GET('/users/:id', noop)
        status, headers, _ = await drive(app, 'DELETE', '/users/9')
        self.assertEqual(status, 405)
        self.assertIn('GET', headers.get('allow', ''))


class HeadRequestTest(IsolatedAsyncioTestCase):
    @staticmethod
    def _page(req, res, ctx):
        res.body = b'hello world'

    async def test_head_is_answered_by_a_get_route_without_a_body(self):
        app = App()
        app.GET('/page', self._page)
        status, _, body = await drive(app, 'HEAD', '/page')
        self.assertEqual(status, 200)
        self.assertEqual(body, b'')

    async def test_get_still_returns_its_body(self):
        app = App()
        app.GET('/page', self._page)
        _, _, body = await drive(app, 'GET', '/page')
        self.assertEqual(body, b'hello world')

    async def test_head_can_be_registered_directly(self):
        app = App()
        app.HEAD('/only', lambda q, s, c: setattr(s, 'status', 204))
        status, _, _ = await drive(app, 'HEAD', '/only')
        self.assertEqual(status, 204)

    async def test_http_helper_covers_head(self):
        app = App()
        app.HTTP('/all', noop)
        status, _, _ = await drive(app, 'HEAD', '/all')
        self.assertEqual(status, 200)


class RouteParameterCoercionTest(IsolatedAsyncioTestCase):
    """Route segments used to convert only `:int` and `:str`, silently handing back a
    string for the other five type names that query hints already supported."""

    UID = '3f2504e0-4f89-11d3-9a0c-0305e82c3301'

    def setUp(self):
        self.seen = {}
        seen = self.seen

        def capture(req, res, ctx):
            seen.clear()
            seen.update(req.params)

        self.app = App()
        for route in ('/i/:v:int', '/s/:v:str', '/f/:v:float', '/b/:v:bool',
                      '/d/:v:date', '/dt/:v:datetime', '/u/:v:uuid', '/n/:v'):
            self.app.GET(route, capture)

    async def test_every_query_hint_type_also_works_in_a_path(self):
        cases = [
            ('/i/42', 42),
            ('/s/abc', 'abc'),
            ('/f/1.5', 1.5),
            ('/b/true', True),
            ('/b/0', False),
            ('/d/2026-08-01', date(2026, 8, 1)),
            ('/dt/2026-08-01T10:30:00', datetime(2026, 8, 1, 10, 30)),
            (f'/u/{self.UID}', UUID(self.UID)),
        ]
        for url, expected in cases:
            status, _, _ = await drive(self.app, 'GET', url)
            self.assertEqual(status, 200, url)
            self.assertEqual(self.seen.get('v'), expected, url)
            self.assertIs(type(self.seen.get('v')), type(expected), url)

    async def test_an_untyped_segment_is_still_a_string(self):
        await drive(self.app, 'GET', '/n/plain')
        self.assertEqual(self.seen.get('v'), 'plain')

    async def test_a_value_that_cannot_convert_is_a_miss(self):
        for url in ('/i/notanint', '/d/not-a-date', '/u/xyz',
                    '/f/abc', '/b/maybe', '/dt/nope'):
            status, _, _ = await drive(self.app, 'GET', url)
            self.assertEqual(status, 404, url)

    async def test_a_failed_conversion_backtracks_to_a_wildcard(self):
        hit = []
        app = App()
        app.GET('/users/:id:int', lambda q, s, c: hit.append(('typed', q.params.get('id'))))
        app.GET('/users/*', lambda q, s, c: hit.append(('wildcard', q.params.get('*'))))

        await drive(app, 'GET', '/users/42')
        self.assertEqual(hit, [('typed', 42)])

        hit.clear()
        await drive(app, 'GET', '/users/abc')
        self.assertEqual(hit, [('wildcard', 'abc')])

    def test_an_unknown_type_is_rejected_at_registration(self):
        for route in ('/x/:v:banana', '/x/:v:uuidd', '/x/:a:b:c'):
            with self.assertRaises(UrlError, msg=route):
                App().GET(route, noop)

    def test_a_parameter_without_a_name_is_rejected(self):
        with self.assertRaises(UrlError):
            App().GET('/x/::int', noop)

    def test_query_hints_keep_their_lenient_boolean(self):
        """Query values that cannot convert stay as the raw string, and an
        unreadable bool stays False rather than becoming a truthy string."""
        for hint, query, expected in [
            ('v:int', b'v=42', 42),
            ('v:float', b'v=1.5', 1.5),
            ('v:date', b'v=2026-08-01', date(2026, 8, 1)),
            ('v:uuid', f'v={self.UID}'.encode(), UUID(self.UID)),
            ('v:bool', b'v=TrUe', True),
            ('v:bool', b'v=garbage', False),
            ('v:int', b'v=garbage', 'garbage'),
        ]:
            request = Request({'query_string': query, 'headers': []}, b'', None, ('www', {}), None)
            request.qh = hint
            value = request.queries.get('v')
            self.assertEqual(value, expected, f'{hint} {query}')
            self.assertIs(type(value), type(expected), f'{hint} {query}')


class MountedDaemonTest(IsolatedAsyncioTestCase):
    """A mounted child's daemons used to be dropped and never start. They are now
    carried onto the parent, still bound to the child they were registered on."""

    @staticmethod
    async def run_lifespan(app, seconds=0.3):
        """Drive the ASGI lifespan protocol. The handler blocks on receive() forever,
        so run it as a task and cancel once daemons have been scheduled."""
        inbox = asyncio.Queue()
        await inbox.put({'type': 'lifespan.startup'})

        async def receive():
            return await inbox.get()

        async def send(message):
            pass

        task = asyncio.create_task(app({'type': 'lifespan'}, receive, send))
        await asyncio.sleep(seconds)
        task.cancel()
        try: await task
        except asyncio.CancelledError: pass

    def setUp(self):
        self.log = []

    def _child(self):
        log = self.log
        child = App()
        child.keep('who', 'child')

        def tick(app):
            log.append(('daemon', app.peek('who')))
            return False        # do not reschedule

        async def boot(app):
            log.append(('startup', app.peek('who')))

        child.daemons = tick
        child.ONCE(boot)
        child.GET('/c', noop)
        return child

    async def test_a_child_daemon_runs_when_the_child_runs_alone(self):
        await self.run_lifespan(self._child())
        self.assertIn(('daemon', 'child'), self.log)

    async def test_a_mounted_child_daemon_is_carried_to_the_parent(self):
        parent = App()
        parent.mount(self._child())
        self.assertEqual(len(parent.daemons), 1)

        await self.run_lifespan(parent)
        self.assertIn(('daemon', 'child'), self.log)

    async def test_a_mounted_daemon_still_sees_the_child_not_the_parent(self):
        """An isolated mount does not share buckets, so a daemon handed the parent
        would read None where it expects the child's own state."""
        parent = App()
        parent.keep('who', 'parent')
        parent.mount(self._child())

        await self.run_lifespan(parent)
        self.assertIn(('daemon', 'child'), self.log)
        self.assertNotIn(('daemon', 'parent'), self.log)

    async def test_the_parents_own_daemons_still_run(self):
        log = self.log
        parent = App()
        parent.keep('who', 'parent')

        def parent_tick(app):
            log.append(('parent-daemon', app.peek('who')))
            return False

        parent.daemons = parent_tick
        parent.mount(self._child())
        self.assertEqual(len(parent.daemons), 2)

        await self.run_lifespan(parent)
        self.assertIn(('parent-daemon', 'parent'), self.log)
        self.assertIn(('daemon', 'child'), self.log)


async def drive_chunked(app, method, path, body, chunk=4096, headers=None, counter=None):
    """Deliver the body in pieces, the way a real server does. `counter` collects how
    many bytes the app actually asked for."""
    position = 0

    async def receive():
        nonlocal position
        piece = body[position:position + chunk]
        position += chunk
        if counter is not None: counter.append(len(piece))
        return {'type': 'http.request', 'body': piece, 'more_body': position < len(body)}

    sent = []

    async def send(message):
        sent.append(message)

    scope = _scope(method, path)
    if headers: scope['headers'] = scope['headers'] + headers
    await app(scope, receive, send)

    status = next((m['status'] for m in sent if m['type'] == 'http.response.start'), None)
    return status, b''.join(m.get('body', b'') for m in sent if m['type'] == 'http.response.body')


class BodySizeLimitTest(IsolatedAsyncioTestCase):
    """The request body was buffered with no ceiling, so a large upload was a memory
    spike and a hostile one was a denial of service."""

    def setUp(self):
        self.app = App(max_body_size=64 * 1024)
        self.app.POST('/up', lambda q, s, c: setattr(s, 'body', b'ok'))

    async def test_a_body_under_the_limit_is_accepted(self):
        status, body = await drive_chunked(self.app, 'POST', '/up', b'x' * 1024)
        self.assertEqual(status, 200)
        self.assertEqual(body, b'ok')

    async def test_a_body_over_the_limit_is_rejected(self):
        status, body = await drive_chunked(self.app, 'POST', '/up', b'x' * (256 * 1024))
        self.assertEqual(status, 413)
        self.assertEqual(body, b'Payload too large')

    async def test_an_oversize_body_is_not_accumulated(self):
        """The limit bounds memory during the request. The body keeps being read, so
        the client can finish sending and actually receive the 413, but nothing past
        the ceiling is retained."""
        payload = b'x' * (8 * 1024 * 1024)      # allocated before tracing starts
        tracemalloc.start()
        status, _ = await drive_chunked(self.app, 'POST', '/up', payload)
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        self.assertEqual(status, 413)
        self.assertLess(peak, 4 * 64 * 1024)    # a small multiple of the 64KB cap

    async def test_no_limit_by_default(self):
        app = App()
        app.POST('/up', lambda q, s, c: setattr(s, 'body', str(len(q.body)).encode()))
        status, body = await drive_chunked(app, 'POST', '/up', b'x' * (512 * 1024))
        self.assertEqual(status, 200)
        self.assertEqual(body, str(512 * 1024).encode())


class StreamingUploadTest(IsolatedAsyncioTestCase):
    """stream=True hands the handler the body in chunks so a large upload is never
    held in memory."""

    def setUp(self):
        self.seen = {}
        seen = self.seen

        async def sink(req, res, ctx):
            total, pieces = 0, 0
            async for chunk in req.stream():
                total += len(chunk)
                pieces += 1
            seen['total'], seen['pieces'] = total, pieces
            res.body = b'stored'

        self.app = App()
        self.app.POST('/upload', sink, stream=True)

    async def test_the_whole_body_reaches_the_handler_in_pieces(self):
        payload = b'y' * (256 * 1024)
        status, body = await drive_chunked(self.app, 'POST', '/upload', payload)
        self.assertEqual(status, 200)
        self.assertEqual(body, b'stored')
        self.assertEqual(self.seen['total'], len(payload))
        self.assertGreater(self.seen['pieces'], 1)

    async def test_the_body_property_explains_itself_on_a_streaming_route(self):
        app = App()

        def peek(req, res, ctx):
            try: req.body
            except RuntimeError as error: res.body = str(error).encode()
            else: res.body = b'no error'

        app.POST('/s', peek, stream=True)
        _, body = await drive_chunked(app, 'POST', '/s', b'abc')
        self.assertIn(b'stream=True', body)
        self.assertIn(b'req.stream()', body)

    async def test_streaming_a_buffered_route_explains_itself(self):
        app = App()

        async def consume(req, res, ctx):
            try:
                async for _ in req.stream(): pass
            except RuntimeError as error: res.body = str(error).encode()
            else: res.body = b'no error'

        app.POST('/p', consume)
        _, body = await drive_chunked(app, 'POST', '/p', b'abc')
        self.assertIn(b'stream=True', body)

    async def test_a_body_can_only_be_streamed_once(self):
        app = App()

        async def twice(req, res, ctx):
            async for _ in req.stream(): pass
            try:
                async for _ in req.stream(): pass
            except RuntimeError as error: res.body = str(error).encode()
            else: res.body = b'no error'

        app.POST('/t', twice, stream=True)
        _, body = await drive_chunked(app, 'POST', '/t', b'abc')
        self.assertIn(b'already been streamed', body)

    async def test_mounting_carries_the_streaming_flag(self):
        parent = App()
        parent.mount(self.app)
        payload = b'z' * (128 * 1024)
        status, _ = await drive_chunked(parent, 'POST', '/upload', payload)
        self.assertEqual(status, 200)
        self.assertEqual(self.seen['total'], len(payload))

    async def test_buffered_routes_are_unaffected(self):
        app = App()
        app.POST('/echo', lambda q, s, c: setattr(s, 'body', q.body))
        app.POST('/json', lambda q, s, c: setattr(s, 'body', q.json))
        _, body = await drive_chunked(app, 'POST', '/echo', b'hello world')
        self.assertEqual(body, b'hello world')
        _, body = await drive_chunked(app, 'POST', '/json', b'{"a":1}')
        self.assertEqual(body, b'{"a":1}')


def _multipart(boundary, fields=(), files=()):
    """A multipart body built the way a browser builds one."""
    pieces = []
    for name, value in fields:
        pieces.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
    for name, filename, content in files:
        pieces.append((
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'
            'Content-Type: application/octet-stream\r\n\r\n'
        ).encode() + content + b'\r\n')
    pieces.append(f'--{boundary}--\r\n'.encode())
    return b''.join(pieces)


MULTIPART = [(b'content-type', b'multipart/form-data; boundary=hb')]
URLENCODED = [(b'content-type', b'application/x-www-form-urlencoded')]


class StreamingFormTest(IsolatedAsyncioTestCase):
    """`await req.form` on a stream=True route parses the body as it arrives, so
    fields are available while file parts spill to a temp file instead of memory."""

    def setUp(self):
        self.seen = {}
        seen = self.seen

        async def accept(req, res, ctx):
            form = await req.form
            file = form.get('data')
            if file is not None:
                seen['filename'] = file.filename
                seen['size'] = file.size
                seen['spilled'] = file._storage._rolled
                if file.size < 1024 * 1024: seen['content'] = file.content
            seen['fields'] = {k: v for k, v in form.to_dict().items() if not isinstance(v, File)}
            res.body = b'ok'

        self.app = App()
        self.app.POST('/form', accept, stream=True)

    async def test_fields_and_a_file_parse_from_the_stream(self):
        payload = os.urandom(100 * 1024)
        body = _multipart('hb', fields=[('note', 'hello'), ('tag', 'a'), ('tag', 'b')],
                          files=[('data', 'blob.bin', payload)])
        status, out = await drive_chunked(self.app, 'POST', '/form', body, headers=MULTIPART)
        self.assertEqual(status, 200)
        self.assertEqual(out, b'ok')
        self.assertEqual(self.seen['fields'], {'note': 'hello', 'tag': ['a', 'b']})
        self.assertEqual(self.seen['filename'], 'blob.bin')
        self.assertEqual(self.seen['size'], len(payload))
        self.assertEqual(self.seen['content'], payload)

    async def test_the_boundary_survives_any_chunk_size(self):
        """The classic bug in hand-rolled multipart parsers is a boundary split
        across a chunk edge. Deliberately awkward chunk sizes, with payload bytes
        that look almost like the delimiter, must all parse identically."""
        payload = b'A\r\n--h' + b'B--hb\r\n' * 5 + b'\r\n--hc--\r\n' + b'\rC\n-D'
        body = _multipart('hb', fields=[('note', 'edge')], files=[('data', 'b.bin', payload)])
        delimiter = len(b'\r\n--hb')
        for chunk in (1, 3, delimiter, delimiter + 1, 4096):
            with self.subTest(chunk=chunk):
                status, _ = await drive_chunked(self.app, 'POST', '/form', body, chunk=chunk, headers=MULTIPART)
                self.assertEqual(status, 200)
                self.assertEqual(self.seen['fields'], {'note': 'edge'})
                self.assertEqual(self.seen['content'], payload)

    async def test_a_large_file_spills_to_disk_and_memory_stays_flat(self):
        """Peak memory while parsing must be a small constant, not a multiple of
        the upload. 16MB arrives, the spool threshold is 256KB, so anything past
        ~1MB of peak means a copy of the payload is being retained somewhere."""
        payload = os.urandom(16 * 1024 * 1024)
        body = _multipart('hb', fields=[('note', 'big')], files=[('data', 'big.bin', payload)])
        size = len(payload)

        tracemalloc.start()
        status, _ = await drive_chunked(self.app, 'POST', '/form', body, headers=MULTIPART)
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        self.assertEqual(status, 200)
        self.assertEqual(self.seen['size'], size)
        self.assertTrue(self.seen['spilled'])
        self.assertLess(peak, 1024 * 1024)

    async def test_a_small_file_stays_in_memory(self):
        body = _multipart('hb', files=[('data', 's.bin', b'tiny')])
        await drive_chunked(self.app, 'POST', '/form', body, headers=MULTIPART)
        self.assertFalse(self.seen['spilled'])
        self.assertEqual(self.seen['content'], b'tiny')

    async def test_reading_the_form_before_awaiting_it_explains_itself(self):
        app = App()

        async def early(req, res, ctx):
            try: req.form.get('note')
            except RuntimeError as error: res.body = str(error).encode()
            else: res.body = b'no error'

        app.POST('/form', early, stream=True)
        body = _multipart('hb', fields=[('note', 'x')])
        _, out = await drive_chunked(app, 'POST', '/form', body, headers=MULTIPART)
        self.assertIn(b'await req.form', out)

    async def test_urlencoded_parses_from_the_stream(self):
        app = App()
        seen = {}

        async def accept(req, res, ctx):
            form = await req.form
            seen.update(form.to_dict())
            res.body = b'ok'

        app.POST('/form', accept, stream=True)
        body = b'username=raymond&email=raymond%40example.com&tag=a&tag=b'
        status, _ = await drive_chunked(app, 'POST', '/form', body, chunk=3, headers=URLENCODED)
        self.assertEqual(status, 200)
        self.assertEqual(seen, {'username': 'raymond', 'email': 'raymond@example.com', 'tag': ['a', 'b']})

    async def test_awaiting_the_form_on_a_buffered_route_is_harmless(self):
        app = App()
        seen = {}

        async def accept(req, res, ctx):
            form = await req.form
            seen['note'] = form.note
            res.body = b'ok'

        app.POST('/form', accept)
        body = _multipart('hb', fields=[('note', 'buffered')])
        status, _ = await drive_chunked(app, 'POST', '/form', body, headers=MULTIPART)
        self.assertEqual(status, 200)
        self.assertEqual(seen['note'], 'buffered')

    async def test_the_form_consumes_the_stream(self):
        app = App()

        async def both(req, res, ctx):
            await req.form
            try:
                async for _ in req.stream(): pass
            except RuntimeError as error: res.body = str(error).encode()
            else: res.body = b'no error'

        app.POST('/form', both, stream=True)
        body = _multipart('hb', fields=[('note', 'x')])
        _, out = await drive_chunked(app, 'POST', '/form', body, headers=MULTIPART)
        self.assertIn(b'already been streamed', out)

    async def test_a_body_without_a_closing_boundary_is_refused(self):
        app = App()

        async def accept(req, res, ctx):
            try: await req.form
            except ValueError as error: res.body = str(error).encode()
            else: res.body = b'no error'

        app.POST('/form', accept, stream=True)
        body = _multipart('hb', fields=[('note', 'x')])[:-8]     # closing boundary cut off
        _, out = await drive_chunked(app, 'POST', '/form', body, headers=MULTIPART)
        self.assertIn(b'closing boundary', out)

    async def test_a_field_past_the_cap_is_refused_after_draining(self):
        """A refused form still reads the rest of the body before the error
        surfaces, so over a real socket the client gets the response instead of a
        connection reset, exactly like the max_body_size path."""
        import heaven.form as form_module
        app = App()

        async def accept(req, res, ctx):
            try: await req.form
            except ValueError as error: res.body = str(error).encode()
            else: res.body = b'no error'

        app.POST('/form', accept, stream=True)
        body = _multipart('hb', fields=[('big', 'x' * (64 * 1024)), ('after', 'yes')])
        counter = []
        ceiling = form_module.FIELD_LIMIT
        form_module.FIELD_LIMIT = 1024
        try:
            _, out = await drive_chunked(app, 'POST', '/form', body, headers=MULTIPART, counter=counter)
        finally:
            form_module.FIELD_LIMIT = ceiling
        self.assertIn(b'FIELD_LIMIT', out)
        self.assertEqual(sum(counter), len(body))

    async def test_a_streamed_file_saves_without_loading(self):
        app = App()
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder, ignore_errors=True)
        target = os.path.join(folder, 'saved.bin')

        async def accept(req, res, ctx):
            form = await req.form
            form.get('data').save(target)
            res.body = b'ok'

        app.POST('/form', accept, stream=True)
        payload = os.urandom(512 * 1024)
        body = _multipart('hb', files=[('data', 'big.bin', payload)])
        status, _ = await drive_chunked(app, 'POST', '/form', body, headers=MULTIPART)
        self.assertEqual(status, 200)
        with open(target, 'rb') as saved:
            self.assertEqual(saved.read(), payload)


class StreamingFormSocketTest(IsolatedAsyncioTestCase):
    """The in-process harness above cannot show connection resets: responding
    mid-upload looks clean there but resets the socket on a real server. These
    tests drive a real uvicorn server to pin the actual receive() semantics."""

    async def _serve(self, app):
        import uvicorn
        config = uvicorn.Config(app, host='127.0.0.1', port=0, log_level='critical', lifespan='off')
        server = uvicorn.Server(config)
        task = asyncio.create_task(server.serve())
        for _ in range(500):
            if server.started: break
            await asyncio.sleep(0.01)
        else: self.fail('uvicorn did not start')
        port = server.servers[0].sockets[0].getsockname()[1]

        async def stop():
            server.should_exit = True
            await asyncio.wait_for(task, 5)
        self.addAsyncCleanup(stop)
        return port

    async def _post(self, port, body, content_type):
        """Send the body in pieces over a raw socket and return the status line."""
        reader, writer = await asyncio.open_connection('127.0.0.1', port)
        writer.write((
            f'POST /form HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n'
            f'Content-Type: {content_type}\r\nContent-Length: {len(body)}\r\n\r\n'
        ).encode())
        for start in range(0, len(body), 64 * 1024):
            writer.write(body[start:start + 64 * 1024])
            await writer.drain()
        status = await asyncio.wait_for(reader.readline(), 10)
        writer.close()
        return status

    async def test_a_20mb_form_parses_over_a_real_socket(self):
        seen = {}
        app = App()

        async def accept(req, res, ctx):
            form = await req.form
            seen['note'] = form.note
            seen['size'] = form.get('data').size
            res.body = b'ok'

        app.POST('/form', accept, stream=True)
        payload = os.urandom(20 * 1024 * 1024)
        body = _multipart('hb', fields=[('note', 'socket')], files=[('data', 'big.bin', payload)])

        port = await self._serve(app)
        status = await self._post(port, body, 'multipart/form-data; boundary=hb')
        self.assertIn(b'200', status)
        self.assertEqual(seen['note'], 'socket')
        self.assertEqual(seen['size'], len(payload))

    async def test_a_refused_form_answers_instead_of_resetting(self):
        """The form hits its field cap early in the upload. The client must still
        be able to finish sending and read a response; without the drain the write
        above fails with a connection reset and no status ever arrives."""
        import heaven.form as form_module
        app = App()

        async def accept(req, res, ctx):
            await req.form
            res.body = b'unreachable'

        app.POST('/form', accept, stream=True)
        body = _multipart('hb', fields=[('big', 'x' * (512 * 1024))],
                          files=[('data', 'big.bin', os.urandom(4 * 1024 * 1024))])

        port = await self._serve(app)
        ceiling = form_module.FIELD_LIMIT
        form_module.FIELD_LIMIT = 1024
        try:
            status = await self._post(port, body, 'multipart/form-data; boundary=hb')
        finally:
            form_module.FIELD_LIMIT = ceiling
        self.assertIn(b'500', status)


async def drive_headers(app, method, path):
    """Like drive() but returns the raw header list, duplicates preserved."""
    sent = []

    async def receive():
        return {'type': 'http.request', 'body': b'', 'more_body': False}

    async def send(message):
        sent.append(message)

    await app(_scope(method, path), receive, send)
    start = next(m for m in sent if m['type'] == 'http.response.start')
    return start['status'], start['headers']


class HeaderSemanticsTest(IsolatedAsyncioTestCase):
    """Setting a header replaces its previous value instead of appending a second
    line. Duplicate singletons like Content-Type are protocol-invalid and clients
    resolve them unpredictably; only Set-Cookie legitimately repeats."""

    @staticmethod
    def _named(headers, name):
        return [v for k, v in headers if k.lower() == name]

    async def test_setting_a_header_twice_sends_it_once_last_write_wins(self):
        app = App()

        def handler(req, res, ctx):
            res.headers = 'X-Robot', 'one'
            res.headers = 'X-Robot', 'two'
            res.body = b'ok'

        app.GET('/h', handler)
        _, headers = await drive_headers(app, 'GET', '/h')
        self.assertEqual(self._named(headers, b'x-robot'), [b'two'])

    async def test_replacement_is_case_insensitive(self):
        app = App()

        def handler(req, res, ctx):
            res.headers = 'Content-Type', 'text/plain'
            res.headers = 'content-type', 'application/json'
            res.body = b'{}'

        app.GET('/h', handler)
        _, headers = await drive_headers(app, 'GET', '/h')
        self.assertEqual(self._named(headers, b'content-type'), [b'application/json'])

    async def test_the_framework_no_longer_doubles_content_type(self):
        """res.file() sets its own Content-Type and Content-Disposition; a handler
        that set either first used to produce two lines on the wire."""
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder, ignore_errors=True)
        filepath = os.path.join(folder, 'page.txt')
        with open(filepath, 'w') as f: f.write('hello')

        app = App()

        def handler(req, res, ctx):
            res.headers = 'Content-Type', 'application/json'
            res.file(filepath)

        app.GET('/h', handler)
        _, headers = await drive_headers(app, 'GET', '/h')
        self.assertEqual(self._named(headers, b'content-type'), [b'text/plain'])
        self.assertEqual(len(self._named(headers, b'content-disposition')), 1)

    async def test_set_cookie_still_accumulates(self):
        app = App()

        def handler(req, res, ctx):
            res.cookie('a', '1')
            res.cookie('b', '2')
            res.body = b'ok'

        app.GET('/h', handler)
        _, headers = await drive_headers(app, 'GET', '/h')
        cookies = self._named(headers, b'set-cookie')
        self.assertEqual(len(cookies), 2)
        self.assertTrue(cookies[0].startswith(b'a=1'))
        self.assertTrue(cookies[1].startswith(b'b=2'))

    async def test_assigning_none_removes_a_header(self):
        app = App()

        def handler(req, res, ctx):
            res.headers = 'X-Debug', 'leaky'
            res.headers = 'X-Debug', None
            res.body = b'ok'

        app.GET('/h', handler)
        _, headers = await drive_headers(app, 'GET', '/h')
        self.assertEqual(self._named(headers, b'x-debug'), [])

    async def test_a_list_value_still_joins_with_commas(self):
        app = App()

        def handler(req, res, ctx):
            res.headers = 'Vary', ['Origin', 'Accept']
            res.body = b'ok'

        app.GET('/h', handler)
        _, headers = await drive_headers(app, 'GET', '/h')
        self.assertEqual(self._named(headers, b'vary'), [b'Origin, Accept'])


class HandlerClassTest(IsolatedAsyncioTestCase):
    """`'package.module.Class#method'` registers a method on a heaven.Handler
    subclass. Heaven builds one instance per request, so `self` is request scoped."""

    async def test_an_async_method_answers_a_request(self):
        app = App()
        app.BEFORE('/orders', lambda q, s, c: setattr(c, 'who', 'hooked'))
        app.GET('/orders', 'tests.controllers.Orders#index')
        status, _, body = await drive(app, 'GET', '/orders')
        self.assertEqual(status, 200)
        self.assertEqual(loads(body), {'route': '/orders', 'who': 'hooked'})

    async def test_a_sync_method_answers_a_request(self):
        app = App()
        app.GET('/orders/:id', 'tests.controllers.Orders#show')
        _, _, body = await drive(app, 'GET', '/orders/7')
        self.assertEqual(body, b'order 7')

    async def test_every_request_gets_its_own_instance(self):
        """The tempting implementation keeps one instance and rebinds req/res per
        request. Two requests in flight would then share `self`, and whichever
        awaits first would resume holding the other's state."""
        controllers.Interleaved.reset()
        app = App()
        app.GET('/slow', 'tests.controllers.Interleaved#slow')

        first, second = await asyncio.gather(
            drive(app, 'GET', '/slow', query=b'n=1'),
            drive(app, 'GET', '/slow', query=b'n=2'),
        )

        self.assertEqual(first[2], b'1')
        self.assertEqual(second[2], b'2')
        self.assertEqual(len(set(controllers.Interleaved.seen)), 2)

    async def test_a_class_handler_can_stream(self):
        app = App()
        app.POST('/upload', 'tests.controllers.Orders#upload', stream=True)
        status, body = await drive_chunked(app, 'POST', '/upload', b'z' * (64 * 1024))
        self.assertEqual(status, 200)
        self.assertEqual(body, str(64 * 1024).encode())

    async def test_a_schema_validates_into_a_class_handler(self):
        app = App()
        app.schema.POST('/orders', expects=controllers.Order)
        app.POST('/orders', 'tests.controllers.Typed#create')
        _, _, body = await drive(app, 'POST', '/orders', body=b'{"reference":"abc"}')
        self.assertEqual(loads(body), {'reference': 'abc'})

    async def test_hooks_can_be_class_methods_too(self):
        app = App()
        app.BEFORE('/orders', 'tests.controllers.Guard#before')
        app.GET('/orders', 'tests.controllers.Orders#index')
        _, _, body = await drive(app, 'GET', '/orders')
        self.assertEqual(loads(body)['who'], 'guarded')

    def test_the_cli_reports_the_class_and_the_real_source(self):
        """`heaven routes` and `heaven handlers` name the handler from what was
        registered and locate it by unwrapping. Unwrapping for the name too would
        reach the bare method and drop the class it belongs to."""
        from heaven.cli import _deep_unwrap

        app = App()
        app.GET('/orders', 'tests.controllers.Orders#index')
        handler = app.subdomains['www'].cache['GET']['/orders']

        self.assertEqual(handler.__name__, 'Orders#index')
        self.assertEqual(handler.__doc__, 'List the orders.')

        original = _deep_unwrap(handler)
        self.assertIs(original, controllers.Orders.index)
        self.assertTrue(inspect.getsourcefile(original).endswith('controllers.py'))
        self.assertIn('async def index', inspect.getsource(original))

    def test_a_class_that_is_not_a_handler_is_refused_at_registration(self):
        with self.assertRaises(HandlerError) as caught:
            App().GET('/x', 'tests.controllers.NotAHandler#index')
        self.assertIn('subclass of heaven.Handler', str(caught.exception))

    def test_a_missing_method_is_refused_at_registration(self):
        with self.assertRaises(HandlerError) as caught:
            App().GET('/x', 'tests.controllers.Orders#nope')
        self.assertIn('no method "nope"', str(caught.exception))

    def test_an_attribute_that_is_not_callable_is_refused(self):
        with self.assertRaises(HandlerError) as caught:
            App().GET('/x', 'tests.controllers.Orders#not_a_method')
        self.assertIn('not callable', str(caught.exception))

    def test_a_spec_without_a_module_path_is_refused(self):
        with self.assertRaises(HandlerError) as caught:
            App().GET('/x', 'Orders#index')
        self.assertIn('needs the module path', str(caught.exception))

    def test_a_spec_without_a_method_is_refused(self):
        with self.assertRaises(HandlerError) as caught:
            App().GET('/x', 'tests.controllers.Orders#')
        self.assertIn('names no method', str(caught.exception))

    def test_a_missing_class_is_refused_at_registration(self):
        with self.assertRaises(HandlerError) as caught:
            App().GET('/x', 'tests.controllers.Absent#index')
        self.assertIn('no class "Absent"', str(caught.exception))

    async def test_function_handlers_are_unaffected(self):
        app = App()
        app.GET('/fn', lambda q, s, c: setattr(s, 'body', b'fn'))
        app.GET('/str', 'tests.controllers.plain')
        _, _, body = await drive(app, 'GET', '/fn')
        self.assertEqual(body, b'fn')
        _, _, body = await drive(app, 'GET', '/str')
        self.assertEqual(body, b'plain')


class OpenApiPathTest(IsolatedAsyncioTestCase):
    class Payload(TypedDict):
        name: str

    def test_parameters_are_braced_and_described(self):
        app = App()
        app.schema.GET('/users/:id', returns=self.Payload)
        spec = app.openapi()
        self.assertIn('/users/{id}', spec['paths'])
        self.assertEqual(spec['paths']['/users/{id}']['get']['parameters'], [
            {'name': 'id', 'in': 'path', 'required': True, 'schema': {'type': 'string'}},
        ])

    def test_typed_parameters_carry_their_type(self):
        app = App()
        app.schema.GET('/orgs/:oid/members/:mid:int', returns=self.Payload)
        spec = app.openapi()
        parameters = spec['paths']['/orgs/{oid}/members/{mid}']['get']['parameters']
        self.assertEqual([p['name'] for p in parameters], ['oid', 'mid'])
        self.assertEqual(parameters[1]['schema']['type'], 'integer')

    def test_routes_without_parameters_have_no_parameters_key(self):
        app = App()
        app.schema.GET('/health', returns=self.Payload)
        spec = app.openapi()
        self.assertNotIn('parameters', spec['paths']['/health']['get'])


class ServerSentEventTest(IsolatedAsyncioTestCase):
    async def test_frames_carry_the_payload_not_its_repr(self):
        async def generator():
            yield {'msg': 'hello'}
            yield 'plain'
            yield b'raw'

        app = App()
        app.GET('/sse', lambda q, s, c: s.stream(generator(), sse=True))
        _, headers, body = await drive(app, 'GET', '/sse')
        self.assertEqual(headers.get('content-type'), 'text/event-stream')
        self.assertEqual(body, b'data: {"msg":"hello"}\n\ndata: plain\n\ndata: raw\n\n')

