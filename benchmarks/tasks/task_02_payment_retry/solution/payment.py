from typing import Callable

class PaymentFailedException(Exception):
    pass

def execute_payment_with_retry(gateway_fn: Callable[[], dict], max_retries: int = 3) -> dict:
    """Execute gateway payment with retry logic."""
    last_err = None
    for attempt in range(max_retries):
        try:
            return gateway_fn()
        except Exception as e:
            last_err = e
    raise PaymentFailedException(f"Payment failed after {max_retries} attempts: {last_err}")

