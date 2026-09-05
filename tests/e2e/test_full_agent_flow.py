"""End-to-End test executing the complete verify-first agent lifecycle:
Task -> Inspect -> Flawed edit -> Initial test failure -> Classify -> Repair -> Verification PASS -> Proof of Done
"""

import subprocess
from pathlib import Path
from terminal_agent.agent.loop import AgentLoop
from terminal_agent.checkpoints.manager import CheckpointManager
from terminal_agent.config.schema import TerminalAgentConfig
from terminal_agent.context.engine import RepositoryContextEngine
from terminal_agent.git.adapter import GitAdapter
from terminal_agent.providers.mock_provider import MockProvider
from terminal_agent.sandbox.local import LocalSandbox
from terminal_agent.security.policy import SecurityPolicyEnforcer
from terminal_agent.security.secrets import SecretGuard
from terminal_agent.session.manager import SessionManager
from terminal_agent.session.models import VerificationStatus
from terminal_agent.telemetry.events import TelemetryLogger
from terminal_agent.tools.registry import ToolRegistry
from terminal_agent.verifier.engine import IndependentVerifier


def test_full_autonomous_repair_flow(tmp_path: Path):
    # 1. Initialize Git Repo
    subprocess.run(["git", "init"], cwd=str(tmp_path), check=True, stdout=subprocess.PIPE)
    subprocess.run(["git", "config", "user.name", "E2ETester"], cwd=str(tmp_path), check=True)
    subprocess.run(["git", "config", "user.email", "e2e@test.local"], cwd=str(tmp_path), check=True)

    # 2. Create sample project with intentional bug
    auth_code = """
import time

def validate_token(token_data: dict) -> bool:
    # BUG: token expiration check is inverted / missing
    if not token_data or "exp" not in token_data:
        return False
    # Flawed logic: Accepts expired token
    return True
"""
    test_code = """
import time
from auth import validate_token

def test_valid_token():
    assert validate_token({"sub": "user1", "exp": time.time() + 3600}) is True

def test_expired_token():
    assert validate_token({"sub": "user1", "exp": time.time() - 3600}) is False
"""
    (tmp_path / "auth.py").write_text(auth_code.strip() + "\n", encoding="utf-8")
    (tmp_path / "test_auth.py").write_text(test_code.strip() + "\n", encoding="utf-8")

    subprocess.run(["git", "add", "."], cwd=str(tmp_path), check=True)
    subprocess.run(["git", "commit", "-m", "initial commit with auth bug"], cwd=str(tmp_path), check=True)

    # 3. Configure Mock Provider to simulate the realistic multi-step flow
    provider = MockProvider()
    
    # Step 1: Read file
    provider.queue_tool_call(
        tool_name="read_file",
        arguments={"path": "auth.py", "reason": "Inspect token expiration logic"}
    )
    # Step 2: First edit attempt (still flawed / syntax issue)
    provider.queue_tool_call(
        tool_name="write_file",
        arguments={
            "path": "auth.py",
            "content": "import time\ndef validate_token(token_data: dict) -> bool:\n    if not token_data or 'exp' not in token_data:\n        return False\n    return token_data['exp'] < time.time()\n",
            "reason": "Invert expiration check (flawed)"
        }
    )
    # Step 3: Trigger verification
    provider.queue_text_response("Applied first fix, ready to verify.")

    # Step 4: After failure is classified and recovery guidance injected, apply correct fix
    provider.queue_tool_call(
        tool_name="write_file",
        arguments={
            "path": "auth.py",
            "content": "import time\ndef validate_token(token_data: dict) -> bool:\n    if not token_data or 'exp' not in token_data:\n        return False\n    return token_data['exp'] > time.time()\n",
            "reason": "Correct token expiration comparison to ensure valid token accepted and expired token rejected"
        }
    )
    # Step 5: Final completion signal
    provider.queue_text_response("Repair completed. All criteria satisfied.")

    # 4. Initialize Core Subsystems
    config = TerminalAgentConfig()
    config.verification.tests = ["pytest test_auth.py"]
    
    secret_guard = SecretGuard(working_dir=tmp_path)
    security_enforcer = SecurityPolicyEnforcer(security_config=config.security, secret_guard=secret_guard)
    sandbox = LocalSandbox(working_dir=tmp_path, default_timeout=30, secret_guard=secret_guard)
    git_adapter = GitAdapter(tmp_path)
    checkpoint_mgr = CheckpointManager(tmp_path)
    session_mgr = SessionManager(tmp_path)
    context_engine = RepositoryContextEngine(tmp_path, secret_guard=secret_guard)

    tool_registry = ToolRegistry(
        working_dir=tmp_path,
        sandbox=sandbox,
        security_enforcer=security_enforcer,
        git_adapter=git_adapter,
        checkpoint_manager=checkpoint_mgr,
        secret_guard=secret_guard
    )

    verifier = IndependentVerifier(
        sandbox=sandbox,
        git_adapter=git_adapter,
        config=config.verification,
        working_dir=tmp_path
    )

    session_state = session_mgr.create_session(task_description="Fix the authentication expiration bug in auth.py")
    telemetry_logger = TelemetryLogger(session_state.session_id, working_dir=tmp_path)

    events_recorded = []
    def on_event(event_type, data):
        events_recorded.append(event_type)

    agent_loop = AgentLoop(
        session_state=session_state,
        config=config,
        provider=provider,
        tool_registry=tool_registry,
        verifier=verifier,
        context_engine=context_engine,
        checkpoint_manager=checkpoint_mgr,
        session_manager=session_mgr,
        telemetry_logger=telemetry_logger,
        step_callback=on_event
    )

    # 5. Run the complete flow
    final_state = agent_loop.run()

    # 6. Verify Results
    assert final_state.current_status == VerificationStatus.VERIFIED
    assert len(final_state.failures) == 1  # Exactly 1 failure was classified and repaired!
    assert final_state.proof_of_done is not None
    assert final_state.proof_of_done["result"] == "VERIFIED ✓"
    assert "auth.py" in final_state.proof_of_done["files_changed"]
    assert "contract_ready" in events_recorded
    assert "repair_plan" in events_recorded
    assert "proof_of_done" in events_recorded

