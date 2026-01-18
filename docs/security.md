# Security & Signing

Heaven takes security seriously. It provides strict, type-safe tools for handling sensitive data, signatures, and secure cookies.

## Secure Serializer

The `heaven.security.SecureSerializer` class is a high-performance alternative to `itsdangerous`. It uses `msgspec` for ultra-fast JSON serialization and `HMAC-SHA256` for signing.

### Basic Usage

```python
from heaven.security import SecureSerializer

# Initialize with a secret key
signer = SecureSerializer(secret_keys="my-super-secret-key")

# data -> signed token
token = signer.dumps({"user_id": 123, "role": "admin"})
print(token) 
# Output: eyJ1c2... . ... .signature

# token -> data
data = signer.loads(token)
print(data)
# Output: {'user_id': 123, 'role': 'admin'}
```

### Expiration (Max Age)

You can enforce expiration on tokens.

```python
try:
    # Valid only for 60 seconds
    data = signer.loads(token, max_age=60)
except SignatureExpired:
    print("Token is too old!")
except BadSignature:
    print("Don't try to hack me!")
```

### Key Rotation

Heaven supports key rotation out of the box. Pass a list of keys to the constructor. 

*   **First Key**: Used for *signing* new data.
*   **All Keys**: Used for *verifying* incoming data.

This allows you to rotate secrets without logging out all active users.

```python
# [New Key, Old Key]
signer = SecureSerializer(secret_keys=["new-secret-2025", "old-secret-2024"])
```

## Strict Schema Validation

Because `SecureSerializer` uses `msgspec` under the hood, you can enforce a schema on the decoded data.

```python
from msgspec import Struct

class UserToken(Struct):
    user_id: int
    role: str

# Returns a UserToken object, or raises error if structure doesn't match
data = signer.loads(token, type=UserToken)
```

## Context Security

Heaven's `Context` object (`ctx`) is protected against accidental overwrites of critical keys.

```python
async def handler(req, res, ctx):
    ctx.my_data = 123 # OK
    
    ctx.session = "hacked" # raises AttributeError!
    # 'session', 'app', 'request', 'response' are reserved.
```

**Next:** It works locally. Let's show the world. On to **[Deployment](deployment.md)**.