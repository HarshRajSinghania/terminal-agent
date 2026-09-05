"""Unit tests for Independent Verification Engine and test output parser."""

from terminal_agent.verifier.runners import TestOutputParser
from terminal_agent.session.models import VerificationStatus


def test_pytest_output_parser():
    sample_output = """
    ============================= test session starts =============================
    collecting ... collected 5 items
    tests/test_auth.py ....F                                                 [100%]
    =================================== FAILURES ===================================
    _____________________________ test_token_expiration ___________________________
    E   AssertionError: Token expired but passed validation
    =========================== 4 passed, 1 failed in 0.15s ===========================
    """
    parsed = TestOutputParser.parse(sample_output, exit_code=1)
    assert parsed.passed == 4
    assert parsed.failed == 1
    assert parsed.total == 5


def test_pytest_all_passed_parser():
    sample_output = "=========================== 5 passed in 0.05s ==========================="
    parsed = TestOutputParser.parse(sample_output, exit_code=0)
    assert parsed.passed == 5
    assert parsed.failed == 0
    assert parsed.total == 5

