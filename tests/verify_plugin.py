
from heaven import Router
import asyncio

class MyPlugin:
    def install(self, app):
        app.keep('plugin_installed', True)
        app.ON('startup', self.check)

    async def check(self, app):
        print("Plugin startup hook called")
        app.keep('plugin_startup', True)

async def main():
    print("Testing Plugin Registration...")
    app = Router()
    app.plugin(MyPlugin())
    
    if app.peek('plugin_installed') is True:
        print("Plugin registered successfully")
    else:
        print("Plugin registration failed")
        exit(1)
        
    print("Testing Plugin Lifecycle...")
    # Simulate startup
    await app._register()
    
    if app.peek('plugin_startup') is True:
        print("Plugin startup hook called successfully")
    else:
        print("Plugin startup hook failed")
        exit(1)

if __name__ == "__main__":
    asyncio.run(main())
