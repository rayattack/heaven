from unittest import TestCase, skip

from routerling import Context, HttpRequest, ResponseWriter, Router


GET_URL = '/v1/customers'
WILDCARD_URL = '/v1/*'
ZAVED = 'this is the value'

class ContextTest(TestCase):
    def setUp(self):
        self.router = Router()
        self.router.BEFORE(WILDCARD_URL, lambda r,w,c: c.keep('yimu', ZAVED))
    
    @skip
    def test_context_seen_across_handlers(self):
        def test_handler(r: HttpRequest, w: ResponseWriter, c: Context):
            self.assertEqual(c.yimu, ZAVED)
        self.router.GET(GET_URL, test_handler)

        mr: HttpRequest = HttpRequest.Mock({})
        mw: ResponseWriter = ResponseWriter.Mock({})
        mc: Context()

        self.router.TEST(GET_URL, mr, mw, mc)
        # can also assert from outside here
        assert mc.yimu == ZAVED
