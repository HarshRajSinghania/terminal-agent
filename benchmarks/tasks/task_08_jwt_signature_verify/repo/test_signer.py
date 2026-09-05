from signer import sign_payload, verify_signature

def test_sign_and_verify_valid():
    secret = "super_secret_key_123"
    data = "user_id:100;role:admin"
    sig = sign_payload(data, secret)
    assert isinstance(sig, str)
    assert len(sig) > 10
    assert verify_signature(data, sig, secret) is True

def test_tampered_payload_rejected():
    secret = "super_secret_key_123"
    data = "user_id:100;role:admin"
    sig = sign_payload(data, secret)
    tampered_data = "user_id:100;role:superadmin"
    assert verify_signature(tampered_data, sig, secret) is False

def test_invalid_secret_rejected():
    data = "user_id:100;role:admin"
    sig = sign_payload(data, "secret_A")
    assert verify_signature(data, sig, "secret_B") is False
