"""Regression cover for defects fixed in 1.5.0.

Each test here pins behaviour that was previously wrong. They drive the real ASGI
entrypoint rather than Earth, because some of the behaviour (HEAD bodies, the error
page) only exists in Router.__call__.
"""
import asyncio
import os
import shutil
import tempfile
from datetime import date, datetime
from typing import TypedDict
from unittest import IsolatedAsyncioTestCase
from uuid import UUID

from heaven import App
from heaven.errors import UrlError
from heaven.request import Request


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

