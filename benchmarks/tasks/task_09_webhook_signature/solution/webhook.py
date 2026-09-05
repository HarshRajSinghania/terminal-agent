import hashlib
import hmac

def verify_webhook(raw_body: str, timestamp_str: str, signature: str, secret: str) -> bool:
    """Verify webhook signature using timestamp and raw payload."""
    canonical = f"{timestamp_str}.{raw_body}"
    expected = hmac.new(secret.encode("utf-8"), canonical.encode("utf-8"), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
