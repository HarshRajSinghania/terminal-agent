import time
from auth import validate_token

def test_valid_token():
    valid_payload = {"sub": "user_42", "exp": time.time() + 1000}
    assert validate_token(valid_payload) is True

def test_expired_token():
    expired_payload = {"sub": "user_42", "exp": time.time() - 100}
    assert validate_token(expired_payload) is False

def test_missing_fields():
    assert validate_token({}) is False
    assert validate_token({"sub": "user_42"}) is False
    assert validate_token(None) is False

