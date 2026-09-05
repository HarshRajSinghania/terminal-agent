"""Unit tests for 12-category failure classification and recovery engine."""

from terminal_agent.recovery.classifier import FailureClassifier
from terminal_agent.recovery.strategies import RecoveryEngine
from terminal_agent.session.models import FailureCategory, SessionState


def test_failure_classification():
    # Syntax Error
    cat, _ = FailureClassifier.classify("SyntaxError: invalid syntax in file.py line 4")
    assert cat == FailureCategory.SYNTAX_ERROR

    # Dependency Error
    cat, _ = FailureClassifier.classify("ModuleNotFoundError: No module named 'cryptography'")
    assert cat == FailureCategory.DEPENDENCY_ERROR

    # Test Failure
    cat, _ = FailureClassifier.classify("AssertionError: Expected 200 got 401")
    assert cat == FailureCategory.TEST_FAILURE

    # Timeout
    cat, _ = FailureClassifier.classify("Command timed out after 60 seconds", timed_out=True)
    assert cat == FailureCategory.TIMEOUT

    # Permission Error
    cat, _ = FailureClassifier.classify("PermissionError: [Errno 13] Permission denied")
    assert cat == FailureCategory.PERMISSION_ERROR


def test_recovery_plan_generation():
    state = SessionState(session_id="test", working_dir=".", task_description="Fix bug")
    hypo, action = RecoveryEngine.analyze_and_plan_recovery(
        FailureCategory.SYNTAX_ERROR,
        'File "auth.py", line 12\n    def foo(\nSyntaxError: unexpected EOF',
        state
    )
    assert "Syntax" in hypo
    assert "syntax" in action.lower() or "repair" in action.lower()

