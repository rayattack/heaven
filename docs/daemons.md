# Background Tasks (Daemons)

Heaven includes a powerful, native system for running background tasks, which we call **Daemons**.

Unlike other frameworks that require external message queues (like Celery or Redis) for simple background work, Heaven lets you run persistent background loops directly within your application process.

## The `app.daemons` API

You can register a background task by assigning a function to `app.daemons`.

```python
import asyncio

# A daemon is just a function that takes 'app' as an argument
async def heartbeat(app):
    print("Thump-thump...")
    # Return the number of seconds to sleep before running again
    return 5 

app.daemons = heartbeat
```

### How it works
1. **Startup**: When the application starts, Heaven launches all registered daemons as independent asyncio tasks.
2. **Loop**: The daemon function is executed.
3. **Sleep**: If the function returns a number (int/float), Heaven waits that many seconds.
4. **Repeat**: The function is called again.

If you return `None` or `False`, the daemon stops runs once and stops.

## Sync vs Async

Heaven supports both synchronous and asynchronous daemons.

### Async (Preferred)
Runs in the main event loop. Ideal for I/O bound tasks like checking databases, sending batched emails, or cleaning up caches.

```python
async def cleanup_tokens(app):
    await db.execute("DELETE FROM tokens WHERE expired = 1")
    return 60 # Run every minute
```

### Sync
Runs in a separate thread pool executor to avoid blocking the main server loop. Useful for CPU-intensive tasks, though heavily CPU-bound work is still better off in a separate process.

```python
def expensive_report(app):
    data = calculate_heavy_report()
    save_to_disk(data)
    return 3600 # Run every hour
```

## Accessing App State

Since daemons receive the `app` instance, they have full access to your shared state, databases, and plugins.

```python
async def mailer(app):
    # Access the shared database connection
    queue = await app.db.fetch_pending_emails()
    
    for email in queue:
        await send_email(email)
        
    return 10 # Check every 10 seconds
```

## Event Loop Monitor

Since Heaven runs on a single thread (asyncio), a single blocking operation can freeze the entire server. Heaven includes a built-in **Watchdog** to warn you if this happens.

```python
# Warn if the event loop is blocked for more than 100ms (0.1s)
app = App(monitor=0.1)
```

If a task blocks the loop, you will see a warning in your logs: `WARNING:heaven.monitor:Event Loop Blocked! Lag: 0.1504s`. This is invaluable for debugging latency spikes.


**Next:** It works locally. Let's show the world. On to **[Deployment](deployment.md)**.