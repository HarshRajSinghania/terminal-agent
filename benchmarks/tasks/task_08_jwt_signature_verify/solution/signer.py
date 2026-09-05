import hashlib
import hmac

def sign_payload(data: str, secret: str) -> str:
    """Compute HMAC SHA256 hex digest for payload."""
    h = hmac.new(secret.encode("utf-8"), data.encode("utf-8"), hashlib.sha256)
    return h.hexdigest()

def verify_signature(data: str, signature: str, secret: str) -> bool:
    """Verify HMAC SHA256 signature using constant-time comparison."""
    expected_sig = sign_payload(data, secret)
    return hmac.compare_digest(expected_sig, signature)

