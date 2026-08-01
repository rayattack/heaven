from heaven import Router
try:
    import asyncpg
except ImportError:
    asyncpg = None

try:
    import msgspec
except ImportError:
    msgspec = None

from typing import Type, TypeVar, List, Any

T = TypeVar("T")

class PendingQuery:
    """
    An awaitable object that allows chaining actions like .bind()
    before executing the query.
    """
    def __init__(self, pool, method: str, query: str, args, kwargs):
        self.pool = pool
        self.method = method
        self.query = query
        self.args = args
        self.kwargs = kwargs
        self.schema = None

    def bind(self, schema: Type[T]) -> 'PendingQuery':
        """
        Bind the result to a msgspec Struct.
        """
        self.schema = schema
        return self

    def __await__(self):
        return self._execute().__await__()

    async def _execute(self):
        # Execute the underlying asyncpg method
        # fetch, fetchrow, fetchval, etc.
        method = getattr(self.pool, self.method)
        result = await method(self.query, *self.args, **self.kwargs)

        if self.schema:
            if self.method == 'fetch':
                # Result is a list of records
                return msgspec.convert(result, List[self.schema])
            elif self.method == 'fetchrow':
                # Result is a single record
                if result:
                    return msgspec.convert(result, self.schema)
                return None
            # fetchval doesn't usually need binding, but if requested:
            return msgspec.convert(result, self.schema)
            
        return result


class HeavenPG:
    def __init__(self, dsn: str = None, name: str = 'db', min_size: int = 10, max_size: int = 10, **kwargs):
        """
        Initialize the PostgreSQL plugin.
        :param dsn: Connection string (e.g. postgres://user:pass@localhost/db)
        :param name: context attribute name (default: 'db', accessible via ctx.db)
        :param min_size: Minimum pool size
        :param max_size: Maximum pool size
        :param kwargs: Additional arguments passed to asyncpg.create_pool
        """
        if asyncpg is None:
            raise ImportError("asyncpg is not installed. Please install it with `pip install asyncpg`.")
        if msgspec is None:
            raise ImportError("msgspec is not installed. Please install it with `pip install msgspec`.")
        
        self.dsn = dsn
        self.name = name
        self.min_size = min_size
        self.max_size = max_size
        self.kwargs = kwargs
        self.pool = None

    def install(self, app: Router):
        """
        The distinct integration point.
        Registers lifecycle hooks and context injection.
        """
        # 1. Register Lifecycle Hooks
        app.ON("startup", self.startup)
        app.ON("shutdown", self.shutdown)

        # 2. Inject into Context
        async def inject_db(req, res, ctx):
            setattr(ctx, self.name, self)
            
        app.BEFORE("/*", inject_db)

    async def startup(self, app):
        """Start the database pool."""
        print(f"Connecting to PostgreSQL ({self.dsn or 'env'})...")
        self.pool = await asyncpg.create_pool(
            dsn=self.dsn,
            min_size=self.min_size,
            max_size=self.max_size,
            **self.kwargs
        )
        print(f"{self.name} connected")

    async def shutdown(self, app):
        """Close the database pool."""
        print(f"Closing {self.name} connection...")
        if self.pool:
            await self.pool.close()
        print(f"{self.name} disconnected")

    # --- Proxy Methods to Pool ---

    async def execute(self, query: str, *args, timeout: float = None) -> str:
        """
        Execute an SQL command (or commands).
        """
        return await self.pool.execute(query, *args, timeout=timeout)

    def fetch(self, query: str, *args, timeout: float = None) -> PendingQuery:
        """
        Prepare a fetch query. Returns an awaitable PendingQuery.
        Usage: 
            await ctx.db.fetch("SELECT ...")
            await ctx.db.fetch("SELECT ...").bind(User)
        """
        return PendingQuery(self.pool, 'fetch', query, args, {'timeout': timeout})

    def fetchrow(self, query: str, *args, timeout: float = None) -> PendingQuery:
        """
        Prepare a fetchrow query.
        """
        return PendingQuery(self.pool, 'fetchrow', query, args, {'timeout': timeout})

    def fetchval(self, query: str, *args, column: int = 0, timeout: float = None) -> PendingQuery:
        """
        Prepare a fetchval query.
        """
        return PendingQuery(self.pool, 'fetchval', query, args, {'column': column, 'timeout': timeout})

    def transaction(self):
        """
        Return a connection that can be used for a transaction.
        """
        return self.pool.acquire()
