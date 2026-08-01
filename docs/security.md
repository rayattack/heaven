# Min 27-28 — Security & Sessions 🔐

Heaven gives you signed sessions and a token signer. It deliberately does **not** give you an auth system — no user model, no password hashing, no OAuth. Those are yours to choose.

## Sessions

```python
app.sessions(secret_key=os.environ['SECRET_KEY'], max_age=86400)
```

Then read and write through the context:

```python
async def login(req, res, ctx):
    ctx.session.user_id = user.id

async def profile(req, res, ctx):
    uid = ctx.session.user_id
    if not uid:
        res.status = 401
        res.abort('Login required')
```

Sessions are **signed cookies**: the data lives in the client's cookie, signed so it can't be tampered with. Heaven sets `httponly=True`, `samesite='Lax'` and `path='/'` by default, and only re-sends the cookie when the session actually changed.

```python
app.sessions(
    secret_key=SECRET,
    cookie_name='__Secure-Session',
    max_age=86400,
    secure=True,           # HTTPS only — set this in production
)
```

!!! danger "Signed does not mean encrypted"
    The payload is base64, not ciphertext. Anyone holding the cookie can read its contents; they just can't change them without the key. **Never put anything secret in a session** — store a user id and look the rest up.

!!! warning "Session writes are lost on an aborted request"
    Sessions save in an `AFTER` hook, and `res.abort()` — including the automatic abort on a 422 validation failure — skips all AFTER hooks. If a request writes to the session and then aborts, that write silently disappears.

!!! note "No server-side sessions, no rotation helper"
    There is no server-side session store and no built-in session-fixation protection. After a privilege change (login, role switch), issue a fresh session yourself rather than reusing the existing one.

## Signing tokens

`SecureSerializer` signs arbitrary JSON-serializable data with HMAC-SHA256 — the same job as `itsdangerous`. Use it for password-reset links, email confirmation tokens, and anything else you hand to a client and expect back unmodified.

```python
from heaven.security import SecureSerializer

signer = SecureSerializer(secret_keys='my-super-secret-key')

token = signer.dumps({'user_id': 123, 'action': 'reset-password'})
# 'eyJ1c2VyX2lkIjo...' — payload.timestamp.signature

data = signer.loads(token)
# {'user_id': 123, 'action': 'reset-password'}
```

### Expiry

Tokens are timestamped at signing, so you can enforce a maximum age when you verify:

```python
from heaven.security import BadSignature, SignatureExpired

try:
    data = signer.loads(token, max_age=900)      # valid for 15 minutes
except SignatureExpired:
    res.status = 410
    res.abort('This link has expired.')
except BadSignature:
    res.status = 400
    res.abort('Invalid link.')
```

`SignatureExpired` is a subclass of `BadSignature` — catch it **first** if you want to tell users apart from attackers.

### Key rotation

Pass a list. The first key signs; every key is tried when verifying, so you can retire a secret without invalidating live tokens.

```python
signer = SecureSerializer(secret_keys=['new-secret-2026', 'old-secret-2025'])
```

Deploy with both, wait longer than your token lifetime, then drop the old one.

### Validating the payload

Pass `type=` to validate the decoded payload against a schema, so a malformed token fails as a `BadSignature` rather than a `KeyError` deep in your handler:

```python
from typing import TypedDict

class ResetToken(TypedDict):
    user_id: int
    action: str

data = signer.loads(token, type=ResetToken)
```

!!! note "Tokens expire in 2106"
    Timestamps are packed as unsigned 32-bit integers, so signed tokens roll over on 7 February 2106. Noting it for completeness rather than urgency.

## The debug error page

```python
app = App(debug=True)   # development only
```

Debug mode is **off by default**. With it off, an unhandled exception returns a plain `500 Internal Server Error` and the traceback is written to your logs.

!!! warning "Only enable `debug` in development"
    In debug mode an unhandled exception renders a "Guardian Angel" page containing the **exception message, full traceback, handler name, and Python version**. If your exception text includes a connection string or credential, that goes straight to the client.

    Leave it off for anything reachable from the internet.

## Serving files from a request path

When a handler builds a file path out of anything the caller supplied, pass `within` so the read cannot leave the directory you meant:

```python
async def download(req, res, ctx):
    res.file(req.params.get('name'), within='/var/lib/app/uploads')
```

Without it, `res.file()` uses the path exactly as given, and a `name` of `../../etc/passwd` reads that file. With it, the path is fully resolved before anything is opened and anything landing outside the root returns 404, which also covers absolute paths and symlinks pointing out of the tree.

This applies to values that reach the path indirectly too, such as a filename read back from a database row that a user controls. `app.ASSETS()` already does this for the folder it mounts. [Serving Files](files.md) covers the details.

## What Heaven does not provide

Being explicit so you don't discover a gap in an incident review:

- **No CSRF protection.** No token generation, no double-submit helper. If you serve HTML forms with cookie sessions, you need this — implement it as a `BEFORE` hook, or rely on `samesite` plus a custom-header check for JSON APIs.
- **No auth utilities.** No JWT, OAuth2, API-key, or HTTP Basic helpers. Bring `pyjwt` or `authlib` and write a `BEFORE` hook.
- **No rate limiting.**
- **No request size limits.** The whole body is buffered in memory before your handler runs — cap it in your reverse proxy.
- **No security headers by default.** [Going to Production](production.md) has a copy-paste hook for these.
- **No HTTPS redirect or trusted-host checks.** Handle both at the proxy.

---

**Next:** Ship it → **[Min 29-30 — Deployment](deployment.md)**
