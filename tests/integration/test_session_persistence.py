"""Integration tests for session persistence, pausing, and resuming."""

from pathlib import Path
from terminal_agent.session.manager import SessionManager
from terminal_agent.session.models import TaskContract, VerificationResult, VerificationStatus


def test_session_lifecycle(tmp_path: Path):
    mgr = SessionManager(working_dir=tmp_path)
    
    contract = TaskContract(
        task_id="task_123",
        task_description="Fix payment retry logic",
        goal="Retry failed payments up to 3 times",
        constraints=["Do not change public API"],
        success_criteria=["Unit tests pass"]
    )
    
    # 1. Create Session
    state = mgr.create_session("Fix payment retry logic", contract=contract)
    session_id = state.session_id
    assert (tmp_path / ".terminal_agent" / "sessions" / f"{session_id}.json").exists()

    # 2. Record Steps
    mgr.record_step(
        state,
        action_type="tool_call",
        tool_name="read_file",
        tool_args={"path": "retry.py"},
        reason="Inspect current retry mechanism",
        output="code contents...",
        status="success"
    )
    assert len(state.completed_steps) == 1
    assert state.metrics.tool_calls == 1

    # 3. Record Verification
    v_res = VerificationResult(
        status=VerificationStatus.PARTIAL,
        tests_run=20,
        tests_passed=18,
        tests_failed=2,
        files_changed_count=1,
        files_changed=["retry.py"]
    )
    mgr.record_verification(state, v_res)
    assert state.current_status == VerificationStatus.PARTIAL

    # 4. Load Session from disk
    restored = mgr.load_session(session_id)
    assert restored is not None
    assert restored.session_id == session_id
    assert restored.contract.task_id == "task_123"
    assert len(restored.completed_steps) == 1
    assert restored.metrics.tests_passed == 18
