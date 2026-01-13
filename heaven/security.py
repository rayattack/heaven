import hmac
import hashlib
import base64
import time
import struct
import typing
from secrets import compare_digest
import msgspec

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
        
        # Pre-instantiate the msgspec Encoder/Decoder for maximum speed.
        # We assume strict compliance, but you can relax this if needed.
        self._encoder = msgspec.json.Encoder()
        self._decoder = msgspec.json.Decoder()

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
        Serializes using msgspec, signs, and timestamps.
        """
        # 1. Serialize Data (msgspec returns bytes directly - FAST)
        # Note: We catch msgspec encoding errors if the object isn't serializable
        try:
            json_bytes = self._encoder.encode(obj)
        except TypeError as e:
            raise SecurityError(f"Serialization failed: {e}")

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
        Verifies token and decodes using msgspec.
        
        :param type: Optional msgspec.Struct type for strict schema validation.
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
                    data = self._decoder.decode(self._base64_decode(b64_data))
                except:
                    data = None
                raise SignatureExpired(f"Token expired {age} seconds ago", payload=data, date_signed=timestamp)

        # --- DECODE DATA (msgspec) ---
        try:
            raw_json = self._base64_decode(b64_data)
            if type:
                # Strict Schema Validation if type is provided
                return msgspec.json.decode(raw_json, type=type)
            else:
                # Generic decoding (returns dict/list)
                return self._decoder.decode(raw_json)
        except msgspec.DecodeError as e:
            raise BadSignature(f"Payload JSON corrupted: {e}")
