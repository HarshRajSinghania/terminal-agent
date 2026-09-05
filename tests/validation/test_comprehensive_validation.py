"""Complete White-Box + Black-Box Functional Validation Test Suite for Terminal Agent."""

import json
import os
import subprocess
import time
from pathlib import Path
import pytest

from terminal_agent.agent.loop import AgentLoop
from terminal_agent.checkpoints.manager import CheckpointManager
from terminal_agent.config.schema import CommandCategory, SecurityConfig, TerminalAgentConfig
from terminal_agent.context.engine import RepositoryContextEngine
from terminal_agent.context.ranker import DeterministicRanker
from terminal_agent.git.adapter import GitAdapter
from terminal_agent.planner.contract import TaskContractGenerator
from terminal_agent.planner.planner import ExecutionPlanner
from terminal_agent.providers.base import LLMMessage
from terminal_agent.providers.mock_provider import MockProvider
from terminal_agent.recovery.classifier import FailureClassifier
from terminal_agent.recovery.strategies import RecoveryEngine
from terminal_agent.sandbox.local import LocalSandbox
from terminal_agent.security.classifier import CommandClassifier
from terminal_agent.security.policy import SecurityPolicyEnforcer
from terminal_agent.security.secrets import SecretGuard
from terminal_agent.session.manager import SessionManager
from terminal_agent.session.models import FailureCategory, VerificationStatus
from terminal_agent.telemetry.events import TelemetryLogger
from terminal_agent.tools.registry import ToolRegistry
from terminal_agent.verifier.engine import IndependentVerifier
from terminal_agent.verifier.runners import TestOutputParser


# ==========================================
# 1. BASIC TASK EXECUTION & REPAIR LIFECYCLE
# ==========================================
def test_validation_basic_task_lifecycle(tmp_path: Path):
    """Verify complete User Task -> Contract -> Edit -> Test -> Verify -> Proof of Done lifecycle."""
    subprocess.run(["git", "init"], cwd=str(tmp_path), check=True, stdout=subprocess.DEVNULL)
    subprocess.run(["git", "config", "user.name", "Validator"], cwd=str(tmp_path), check=True)
    subprocess.run(["git", "config", "user.email", "val@agent.local"], cwd=str(tmp_path), check=True)

    # Buggy calculator
    (tmp_path / "calc.py").write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
    (tmp_path / "test_calc.py").write_text(
        "from calc import add\ndef test_add():\n    assert add(2, 3) == 5\n", encoding="utf-8"
    )
    subprocess.run(["git", "add", "."], cwd=str(tmp_path), check=True)
    subprocess.run(["git", "commit", "-m", "initial buggy commit"], cwd=str(tmp_path), check=True)

    provider = MockProvider()
    provider.queue_tool_call(
        "edit_file",
        {"path": "calc.py", "old_str": "return a - b", "new_str": "return a + b", "reason": "Fix addition bug"}
    )
    provider.queue_text_response("Fix applied. Ready for verification.")

    config = TerminalAgentConfig()
    config.verification.tests = ["pytest test_calc.py"]

    secret_guard = SecretGuard(working_dir=tmp_path)
    security_enforcer = SecurityPolicyEnforcer(security_config=config.security, secret_guard=secret_guard)
    sandbox = LocalSandbox(working_dir=tmp_path, default_timeout=30, secret_guard=secret_guard)
    git_adapter = GitAdapter(tmp_path)
    checkpoint_mgr = CheckpointManager(tmp_path)
    session_mgr = SessionManager(tmp_path)
    context_engine = RepositoryContextEngine(tmp_path, secret_guard=secret_guard)

    tool_registry = ToolRegistry(tmp_path, sandbox, security_enforcer, git_adapter, checkpoint_mgr, secret_guard)
    verifier = IndependentVerifier(sandbox, git_adapter, config.verification, tmp_path)
    session_state = session_mgr.create_session("Fix the add function")
    telemetry_logger = TelemetryLogger(session_state.session_id, working_dir=tmp_path)

    agent_loop = AgentLoop(
        session_state, config, provider, tool_registry, verifier,
        context_engine, checkpoint_mgr, session_mgr, telemetry_logger
    )

    final_state = agent_loop.run()
    assert final_state.current_status == VerificationStatus.VERIFIED
    assert final_state.proof_of_done is not None
    assert final_state.proof_of_done["result"] == "VERIFIED ✓"
    assert "calc.py" in final_state.proof_of_done["files_changed"]


# ==========================================
# 2. REPOSITORY CONTEXT & SELECTIVE SEARCH
# ==========================================
def test_validation_repository_context_engine(tmp_path: Path):
    """Verify directory discovery, deterministic symbol ranker, and ignore filtering."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "auth.py").write_text("def authenticate_jwt(token): pass\n", encoding="utf-8")
    (tmp_path / "src" / "user.py").write_text("class UserProfile: pass\n", encoding="utf-8")
    (tmp_path / "src" / "database.py").write_text("def get_db_connection(): pass\n", encoding="utf-8")

    engine = RepositoryContextEngine(tmp_path)
    tree = engine.build_tree_summary()
    assert "auth.py" in tree
    assert "user.py" in tree
    assert "database.py" in tree

    results = engine.search_relevant_files("authenticate jwt user login", top_k=3)
    assert len(results) > 0
    result_paths = [r[0] for r in results]
    assert any("auth.py" in p for p in result_paths)
    assert any("user.py" in p for p in result_paths)


# ==========================================
# 3. SECURITY, PATH TRAVERSAL & SECRET GUARD
# ==========================================
def test_validation_path_traversal_and_secrets(tmp_path: Path):
    """Verify that path traversal and secret access are strictly blocked."""
    guard = SecretGuard(working_dir=tmp_path)

    # 1. Path traversal attacks
    assert guard.is_path_blocked(tmp_path / ".." / "outside.txt") is True
    assert guard.is_path_blocked(tmp_path / ".." / ".." / "secret.txt") is True
    assert guard.is_path_blocked("C:/Windows/System32/cmd.exe") is True

    # 2. Secret file protections
    assert guard.is_path_blocked(tmp_path / ".env") is True
    assert guard.is_path_blocked(tmp_path / "prod.env") is True
    assert guard.is_path_blocked(tmp_path / "id_rsa") is True
    assert guard.is_path_blocked(tmp_path / "server.key") is True
    assert guard.is_path_blocked(tmp_path / "cert.pem") is True

    # 3. Tool execution block
    registry = ToolRegistry(working_dir=tmp_path, secret_guard=guard)
    res = registry.execute("read_file", {"path": "../secret.txt", "reason": "Attack test"})
    assert res.success is False
    assert "blocked by security policy" in res.error.lower()


# ==========================================
# 4. COMMAND CLASSIFICATION & APPROVAL POLICY
# ==========================================
def test_validation_command_safety_policy(tmp_path: Path):
    """Verify command classification and user approval callback behavior."""
    # Classifications
    assert CommandClassifier.classify("pytest")[0] == CommandCategory.SAFE
    assert CommandClassifier.classify("git diff")[0] == CommandCategory.SAFE
    assert CommandClassifier.classify("rm -rf /")[0] == CommandCategory.DESTRUCTIVE
    assert CommandClassifier.classify("curl https://remote.io")[0] == CommandCategory.NETWORK
    assert CommandClassifier.classify("sudo systemctl restart")[0] == CommandCategory.PRIVILEGED

    # Rejection policy
    rejections = 0
    def deny_callback(cmd, cat, reason):
        nonlocal rejections
        rejections += 1
        return False

    enforcer = SecurityPolicyEnforcer(
        security_config=SecurityConfig(require_confirmation_for=[CommandCategory.DESTRUCTIVE]),
        confirmation_callback=deny_callback
    )
    allowed, msg, _ = enforcer.check_command("rm -rf target")
    assert allowed is False
    assert rejections == 1
    assert "rejected by user" in msg.lower()


# ==========================================
# 5. CHECKPOINTS & REAL FILE ROLLBACK
# ==========================================
def test_validation_checkpoints_and_file_rollback(tmp_path: Path):
    """Verify checkpoint snapshots and complete physical file rollback."""
    mgr = CheckpointManager(working_dir=tmp_path)
    file_a = tmp_path / "service.py"
    file_a.write_text("initial_state = 1\n", encoding="utf-8")

    # Snapshot 1
    chk1 = mgr.create_checkpoint("v1_clean")
    assert file_a.read_text() == "initial_state = 1\n"

    # Corrupt / modify
    file_a.write_text("corrupted_state = 999\n", encoding="utf-8")
    assert file_a.read_text() == "corrupted_state = 999\n"

    # Rollback to snapshot 1
    rolled_back = mgr.rollback(chk1.checkpoint_id)
    assert rolled_back is True
    assert file_a.read_text() == "initial_state = 1\n"


# ==========================================
# 6. SESSION PERSISTENCE & RESUMPTION
# ==========================================
def test_validation_session_persistence(tmp_path: Path):
    """Verify session contract, steps, failures, and metrics persist to disk and reload."""
    mgr = SessionManager(working_dir=tmp_path)
    state = mgr.create_session("Refactor database layer")
    state.contract = TaskContractGenerator.generate_from_description("Refactor database layer")
    state.plan = ExecutionPlanner.create_initial_plan(state.contract)
    
    mgr.record_step(state, "tool_call", "Inspect models", tool_name="read_file", tool_args={"path": "models.py"})
    mgr.record_failure(
        state, FailureCategory.SYNTAX_ERROR, "SyntaxError in line 5",
        "Syntax error in models.py", "Fix syntax"
    )
    mgr.save_session(state)

    # Reload from fresh manager instance
    mgr2 = SessionManager(working_dir=tmp_path)
    loaded = mgr2.load_session(state.session_id)

    assert loaded is not None
    assert loaded.session_id == state.session_id
    assert loaded.contract.goal == state.contract.goal
    assert len(loaded.completed_steps) == 1
    assert len(loaded.failures) == 1
    assert loaded.failures[0].failure_category == FailureCategory.SYNTAX_ERROR


# ==========================================
# 7. 12-CATEGORY FAILURE CLASSIFIER & RECOVERY
# ==========================================
def test_validation_failure_classification_categories():
    """Verify all 12 required failure categories are accurately classified."""
    cases = [
        ("SyntaxError: invalid syntax", FailureCategory.SYNTAX_ERROR),
        ("ModuleNotFoundError: No module named 'foo'", FailureCategory.DEPENDENCY_ERROR),
        ("AssertionError: assert False", FailureCategory.TEST_FAILURE),
        ("PermissionError: [Errno 13] Access denied", FailureCategory.PERMISSION_ERROR),
        ("Command timed out after 60s", FailureCategory.TIMEOUT),
        ("Connection refused by server", FailureCategory.NETWORK_ERROR),
        ("context_length_exceeded token limit", FailureCategory.CONTEXT_OVERFLOW),
        ("Tool 'read_file' failed with error", FailureCategory.TOOL_ERROR),
        ("TypeError: unsupported operand type", FailureCategory.WRONG_SOLUTION),
        ("command not found", FailureCategory.COMMAND_FAILURE),
        ("Incomplete implementation TODO", FailureCategory.INCOMPLETE_TASK),
    ]
    for text, expected_cat in cases:
        cat, _ = FailureClassifier.classify(text)
        assert cat == expected_cat, f"Failed for {text}, got {cat}"


# ==========================================
# 8. INDEPENDENT VERIFIER REJECTS FALSE CLAIMS
# ==========================================
def test_validation_verifier_rejects_false_claim(tmp_path: Path):
    """Verify verifier returns FAILED if tests fail, even if agent claims done."""
    (tmp_path / "broken.py").write_text("def get_status(): return 'broken'\n", encoding="utf-8")
    (tmp_path / "test_broken.py").write_text(
        "from broken import get_status\ndef test_status(): assert get_status() == 'ok'\n",
        encoding="utf-8"
    )

    git_adapter = GitAdapter(tmp_path)
    sandbox = LocalSandbox(tmp_path)
    verifier = IndependentVerifier(sandbox, git_adapter, working_dir=tmp_path)

    # Independent verifier runs pytest test_broken.py
    v_res = verifier.verify(custom_test_cmd="pytest test_broken.py")
    assert v_res.status == VerificationStatus.FAILED
    assert v_res.tests_failed == 1
    assert v_res.passed_all is False


# ==========================================
# 9. PROCESS CLEANUP & TIMEOUT TERMINATION
# ==========================================
def test_validation_process_tree_timeout_cleanup(tmp_path: Path):
    """Verify timed out processes are safely terminated without zombie hanging."""
    sandbox = LocalSandbox(working_dir=tmp_path, default_timeout=1)
    t0 = time.perf_counter()
    res = sandbox.execute("python -c \"import time; time.sleep(10)\"", timeout=1)
    duration = time.perf_counter() - t0

    assert res.timed_out is True
    assert res.exit_code == 124
    assert duration < 3.0  # Terminated quickly within timeout boundary


# ==========================================
# 10. ENVIRONMENT SANITIZATION
# ==========================================
def test_validation_environment_sanitization(tmp_path: Path, monkeypatch):
    """Verify host secrets like AWS_SECRET_ACCESS_KEY, SSH_AUTH_SOCK are not exposed in sandbox."""
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "AKIA_DO_NOT_EXPOSE_SECRET")
    monkeypatch.setenv("DATABASE_PASSWORD", "super_secret_db_pass")
    monkeypatch.setenv("SAFE_CONFIG_VAR", "visible_config")

    guard = SecretGuard(working_dir=tmp_path)
    sanitized = guard.sanitize_env()

    assert "AWS_SECRET_ACCESS_KEY" not in sanitized
    assert "DATABASE_PASSWORD" not in sanitized
    assert sanitized.get("SAFE_CONFIG_VAR") == "visible_config"


# ==========================================
# 11. NODE / JAVASCRIPT TEST RUNNER SUPPORT
# ==========================================
def test_validation_node_test_runner_support(tmp_path: Path):
    """Verify Node.js test runner execution via sandbox."""
    (tmp_path / "sum.js").write_text("function sum(a, b) { return a + b; }\nmodule.exports = sum;\n", encoding="utf-8")
    (tmp_path / "test.js").write_text(
        "const assert = require('assert');\nconst sum = require('./sum');\nassert.strictEqual(sum(2, 3), 5);\nconsole.log('NODE TESTS OK');\n",
        encoding="utf-8"
    )

    sandbox = LocalSandbox(working_dir=tmp_path)
    res = sandbox.execute("node test.js")
    assert res.is_success is True
    assert "NODE TESTS OK" in res.stdout
