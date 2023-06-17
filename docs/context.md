#### Mambo number 3. Context
All handlers receive this as the third argument i.e. **`...(..., ..., c: Context)`** to help with preserving state across a request lifecycle i.e. from start/reciept to finish/response.

- **`c.keep(alias: str, value: any)`** -> Save something that can be retrieved via [Python descriptor]() semantics. i.e. `c.alias` will return the kept value.

-----------------------