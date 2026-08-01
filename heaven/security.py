import hmac
import hashlib
import base64
import time
import struct
import typing
from secrets import compare_digest
from typing import Union, Optional
from orjson import dumps, loads, JSONDecodeError
from pytastic import Pytastic
from pytastic.exceptions import ValidationError

# --- Custom Exceptions ---
class SecurityError(Exception):
    """Base exception for all security related errors."""
    pass

class BadSignature(SecurityError):
    """Raised when the signature does not match the data."""
    pass

class SignatureExpired(BadSignature):
    """Raised when the signature is valid but the token has expired."""
    def __init__(self, message, payload=None, date_signed=None):
        super().__init__(message)
        self.payload = payload
        self.date_signed = date_signed

# --- The Core Class ---
class SecureSerializer:
    def __init__(
        self, 
        secret_keys: typing.Union[str, typing.List[str]], 
        salt: str = "app-context", 
        digest_method=hashlib.sha256
    ):
        if isinstance(secret_keys, str):
            self.secret_keys = [secret_keys.encode('utf-8')]
        else:
            self.secret_keys = [k.encode('utf-8') for k in secret_keys]
            
        self.salt = salt.encode('utf-8')
        self.digest_method = digest_method
        
    def _derive_key(self, secret_key: bytes) -> bytes:
        return hmac.new(secret_key, self.salt, self.digest_method).digest()

    def _base64_encode(self, data: bytes) -> bytes:
        return base64.urlsafe_b64encode(data).rstrip(b'=')

    def _base64_decode(self, data: bytes) -> bytes:
        pad = b'=' * (-len(data) % 4)
        return base64.urlsafe_b64decode(data + pad)

    def _sign(self, value: bytes, key: bytes) -> bytes:
        sig = hmac.new(key, value, self.digest_method).digest()
        return self._base64_encode(sig)

    def dumps(self, obj: typing.Any) -> str:
        """
        Serializes using json, signs, and timestamps.
        """
        # 1. Serialize Data
        try: json_bytes = dumps(obj)
        except TypeError as e: raise SecurityError(f"Serialization failed: {e}")

        # 2. Create Timestamp
        timestamp = int(time.time())
        ts_bytes = struct.pack('>I', timestamp)
        
        # 3. Construct Payload
        # Structure: Base64(JsonBytes).Base64(TimestampBytes)
        payload = self._base64_encode(json_bytes) + b'.' + self._base64_encode(ts_bytes)
        
        # 4. Sign with PRIMARY key
        derived_key = self._derive_key(self.secret_keys[0])
        signature = self._sign(payload, derived_key)
        
        return (payload + b'.' + signature).decode('utf-8')

    def loads(self, token: typing.Union[str, bytes], max_age: int = None, type: typing.Type = None) -> typing.Any:
        """
        Verifies token and decodes using json.
        
        :param type: Optional Type for Pytastic validation.
        """
        if isinstance(token, str):
            token = token.encode('utf-8')

        try:
            payload, signature = token.rsplit(b'.', 1)
            b64_data, b64_ts = payload.split(b'.', 1)
        except ValueError:
            raise BadSignature("Invalid token format")

        # --- KEY ROTATION CHECK ---
        client_sig_valid = False
        for secret in self.secret_keys:
            derived_key = self._derive_key(secret)
            expected_sig = self._sign(payload, derived_key)
            if compare_digest(signature, expected_sig):
                client_sig_valid = True
                break
        
        if not client_sig_valid:
            raise BadSignature("Signature mismatch")

        # --- EXPIRATION CHECK ---
        try:
            ts_bytes = self._base64_decode(b64_ts)
            timestamp = struct.unpack('>I', ts_bytes)[0]
        except Exception:
            raise BadSignature("Invalid timestamp format")

        if max_age is not None:
            age = time.time() - timestamp
            if age > max_age:
                # Try to decode mainly for the error message context
                try:
                    data = loads(self._base64_decode(b64_data).decode('utf-8'))
                except:
                    data = None
                raise SignatureExpired(f"Token expired {age} seconds ago", payload=data, date_signed=timestamp)

        # --- DECODE DATA ---
        try:
            raw_json = self._base64_decode(b64_data).decode('utf-8')
            data = loads(raw_json)
            
            if type:
                # Strict Schema Validation if type is provided
                return Pytastic().validate(type, data)
            else:
                # Generic decoding (returns dict/list)
                return data
        except JSONDecodeError as e:
            raise BadSignature(f"Payload JSON corrupted: {e}")
        except ValidationError as e:
            raise BadSignature(f"Validation failed: {e}")
