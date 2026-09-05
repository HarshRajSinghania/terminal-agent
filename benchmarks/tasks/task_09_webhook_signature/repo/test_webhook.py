import hashlib
import hmac
from webhook import verify_webhook

def _compute_expected_sig(raw_body: str, timestamp_str: str, secret: str) -> str:
    canonical = f"{timestamp_str}.{raw_body}"
    return hmac.new(secret.encode("utf-8"), canonical.encode("utf-8"), hashlib.sha256).hexdigest()

def test_webhook_valid_signature():
    secret = "whsec_abc123"
    body = '{"event": "charge.success", "amount": 2500}'
    ts = "1725500000"
    sig = _compute_expected_sig(body, ts, secret)

    assert verify_webhook(body, ts, sig, secret) is True

def test_webhook_invalid_signature():
    secret = "whsec_abc123"
    body = '{"event": "charge.success", "amount": 2500}'
    ts = "1725500000"

    assert verify_webhook(body, ts, "invalid_hex_signature", secret) is False
