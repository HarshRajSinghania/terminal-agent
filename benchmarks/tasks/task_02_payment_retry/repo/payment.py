from typing import Callable

class PaymentFailedException(Exception):
    pass

def execute_payment_with_retry(gateway_fn: Callable[[], dict], max_retries: int = 3) -> dict:
    """Execute gateway payment with retry logic."""
    # Starter implementation: does not retry
    return gateway_fn()
