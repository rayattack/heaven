
from heaven import Router
import pytest

class MyPlugin:
    def install(self, app):
        app.keep('plugin_installed', True)
        app.ON('startup', self.check)

    async def check(self, app):
        app.keep('plugin_startup', True)

def test_plugin_registration():
    app = Router()
    app.plugin(MyPlugin())
    
    assert app.peek('plugin_installed') is True

@pytest.mark.asyncio
async def test_plugin_lifecycle():
    app = Router()
    plugin = MyPlugin()
    app.plugin(plugin)
    
    # Simulate startup
    await app._register()
    
    assert app.peek('plugin_startup') is True

def test_plugin_bad_protocol():
    app = Router()
    class BadPlugin: pass
    
    with pytest.raises(ValueError):
        app.plugin(BadPlugin())
