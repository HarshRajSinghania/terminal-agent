import pytest
from payment import execute_payment_with_retry, PaymentFailedException

def test_payment_succeeds_first_attempt():
    calls = 0
    def gateway():
        nonlocal calls
        calls += 1
        return {"status": "success", "tx_id": "tx_123"}

    res = execute_payment_with_retry(gateway, max_retries=3)
    assert res["status"] == "success"
    assert calls == 1

def test_payment_succeeds_after_retry():
    calls = 0
    def gateway():
        nonlocal calls
        calls += 1
        if calls < 3:
            raise ConnectionError("Temporary network blip")
        return {"status": "success", "tx_id": "tx_789"}

    res = execute_payment_with_retry(gateway, max_retries=3)
    assert res["status"] == "success"
    assert calls == 3

def test_payment_fails_after_max_retries():
    calls = 0
    def gateway():
        nonlocal calls
        calls += 1
        raise ConnectionError("Gateway down")

    with pytest.raises(PaymentFailedException):
        execute_payment_with_retry(gateway, max_retries=3)
    assert calls == 3
