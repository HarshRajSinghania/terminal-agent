import hashlib
import hmac

def verify_webhook(raw_body: str, timestamp_str: str, signature: str, secret: str) -> bool:
    # BUG: incorrect concatenation separator
    canonical = f"{raw_body}:{timestamp_str}"
    expected = hmac.new(secret.encode("utf-8"), canonical.encode("utf-8"), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
