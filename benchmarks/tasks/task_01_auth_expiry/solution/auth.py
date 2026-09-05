import time

def validate_token(payload: dict) -> bool:
    """Validate token payload structure and expiration."""
    if not payload or not isinstance(payload, dict):
        return False
    if "exp" not in payload or "sub" not in payload:
        return False
    return payload["exp"] > time.time()

