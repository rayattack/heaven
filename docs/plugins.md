# Plugins

Heaven provides a simple yet powerful plugin system that allows you to extend the framework's functionality, integrate with databases, or add custom behavior.

## The Plugin Protocol

A plugin is simply a class (or object) that implements an `install` method. This method receives the application instance (`Router`) as its only argument, allowing you to register hooks, inject context, or modify configuration.

```python
class MyPlugin:
    def install(self, app):
        # Register hooks
        app.ON('startup', self.connect)
        
        # Inject into context
        app.keep('my_plugin', self)

    async def connect(self, app):
        print("Plugin connected!")
```

## Using Plugins

Registering a plugin is done via `app.plugin()`:

```python
app = Router()
app.plugin(MyPlugin())
```

## Plugin Marketplace

Looking for ready-made plugins? Check out the **[Plugin Marketplace](marketplace.md)** for community plugins and integrations.

## Advanced Example: `pg_heaven`

Here is a complete example of a PostgreSQL plugin that integrates seamless `msgspec` destructuring for high-performance data retrieval.

### The Plugin

```python
import msgspec
import asyncpg
from typing import Type, TypeVar, List, Any

T = TypeVar("T")

class PostgresPlugin:
    def __init__(self, dsn: str, name: str = "pg"):
        self.dsn = dsn
        self.name = name
        self.pool = None

    def install(self, app):
        """The distinct integration point."""
        
        # 1. Register Lifecycle Hooks
        # Heaven automatically manages the pool connection/disconnection
        app.ON("startup", self.startup)
        app.ON("shutdown", self.shutdown)

        # 2. Inject into Context
        # Using a BEFORE hook ensures 'ctx.pg' is available on every request
        # with zero overhead for the end-user
        async def inject_db(req, res, ctx):
            # This makes 'ctx.db' or 'ctx.pg' available
            setattr(ctx, self.name, self)
            
        app.BEFORE("/*", inject_db)

    async def startup(self, app):
        self.pool = await asyncpg.create_pool(self.dsn)
        print(f"🔌 {self.name} connected")

    async def shutdown(self, app):
        await self.pool.close()
        print(f"🔌 {self.name} disconnected")

    # The Magic Method: Msgspec Integration
    async def fetch(self, query: str, *args, bind: Type[T] = None) -> List[T] | List[Any]:
        """
        Executes query and seamlessly destructures into a msgspec Struct 
        if 'bind' is provided.
        """
        rows = await self.pool.fetch(query, *args)
        
        if bind:
            # fast-path: asyncpg Record -> dict -> msgspec Struct
            # msgspec.convert is extremely fast at this
            return msgspec.convert(rows, List[bind])
            
        return rows
```

### Usage in Application

This setup allows for implicit context availability and explicit, typed destructuring.

```python
from heaven import Router
import msgspec

# 1. Define your data structure
class User(msgspec.Struct):
    id: int
    email: str
    is_active: bool

app = Router()

# 2. Register (once)
app.plugin(PostgresPlugin(dsn="postgres://user:pass@localhost/db", name="db"))

# 3. Use in handler
async def get_users(req, res, ctx):
    # 'ctx.db' is auto-injected
    # 'bind=User' automatically converts the SQL result to List[User]
    users = await ctx.db.fetch("SELECT * FROM users", bind=User)
    
    # 'users' is now a list of Structs, ready for validation or automatic encoding
    res.body = users

app.GET("/users", get_users)
```
