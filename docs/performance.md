# Performance

Heaven claims to be fast. This page shows the measurements behind that claim, including the cases where it doesn't win.

!!! note "How to read these numbers"
    All figures below were measured on one machine (Intel i5-8350U, CPython 3.12.3) with garbage collection disabled during timing, 5+ warmup rounds, and the **median** of 7 rounds reported. Your absolute numbers will differ; the ratios are the interesting part.

    Every benchmark here is a microbenchmark of *framework overhead*. Once your handler talks to a database, that overhead is rounding error — a 100 µs framework difference is invisible next to a 5 ms query. Optimize your I/O first.

## Validation: pytastic vs pydantic

Heaven validates with [pytastic](https://rayattack.github.io/pytastic/) (pure Python, zero dependencies); FastAPI validates with pydantic v2 (a compiled Rust core). Equivalent schemas and identical input on both sides.

| Case | pytastic | pydantic v2 | Result |
| :--- | ---: | ---: | :--- |
| Flat object, 3 fields | **771,456/s** | 575,652/s | pytastic **+34%** |
| Nested object, 3 items | **236,736/s** | 158,644/s | pytastic **+49%** |
| Wide object, 50 items | **27,858/s** | 21,195/s | pytastic **+31%** |
| Invalid input (raises) | **437,482/s** | 393,978/s | pytastic **+11%** |

Pure Python beating a Rust core sounds implausible until you look at where the time goes: pydantic pays a fixed FFI cost crossing into Rust and constructing a model instance, while pytastic generates specialized Python code per schema and returns a plain `dict`. At these object sizes, the crossing costs more than the validating.

### Where pydantic wins

Validating **straight from JSON bytes** — the actual shape of a web request — pydantic parses and validates in a single pass inside Rust, while Heaven decodes with `orjson` first and then validates:

| Path | Throughput |
| :--- | ---: |
| pytastic — `orjson.loads()` then `validate()` | 166,293/s |
| pydantic — `model_validate_json()` | **174,309/s** |

So pydantic is ~5% faster on the end-to-end JSON path even though it is 49% slower once the data is already a dict. Two honest caveats on the comparison as a whole:

- **pytastic stops at the first error; pydantic collects them all.** Reporting every failure is more work and more useful. Some of pytastic's error-path advantage is that it does less.
- **pytastic returns a `dict`; pydantic returns a typed model** with validators, serializers, and computed fields. It is doing more than shape-checking.

## Making your own app fast

The framework is rarely your bottleneck. In rough order of impact:

1. **Never block the event loop.** One synchronous database call inside an `async def` stalls every concurrent request. Run `App(monitor=0.1)` in development to catch it — see [Background Work](daemons.md#catching-a-blocked-loop).
2. **Serve static files from your proxy**, not `app.ASSETS()`.
3. **Use `--workers N`** to use more than one core. Python's GIL means one process saturates one core, whatever the framework.
4. **Keep `res.defer()` callbacks short** — the connection stays open until they finish.
5. **Assign `dict` to `res.body`** rather than serializing by hand; Heaven's path uses `orjson` already.


---


## Reproducing Heaven vs FastAPI (Home Claims)

The benchmark scripts are not shipped in the repo. To rebuild them, drive each app's ASGI callable directly:

```python
async def one_request(app, scope, body):
    async def receive():
        return {'type': 'http.request', 'body': body, 'more_body': False}
    sent = []
    async def send(message):
        sent.append(message)
    await app(dict(scope), receive, send)
    return sent
```

Time a large loop of that, disable `gc` inside the timed section, and take a median across rounds. Avoid `time.sleep`, avoid the network, and don't compare a sync FastAPI handler against an async Heaven one — sync handlers get dispatched to a thread pool and the comparison stops being about the framework.

