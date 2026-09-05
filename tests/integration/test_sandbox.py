"""Integration tests for sandbox execution, timeouts, and process cleanup."""

import sys
from pathlib import Path
from terminal_agent.sandbox.local import LocalSandbox


def test_local_sandbox_execution(tmp_path: Path):
    sandbox = LocalSandbox(working_dir=tmp_path, default_timeout=5)

    # Simple successful execution
    res = sandbox.execute("python -c \"print('sandbox ok')\"")
    assert res.is_success is True
    assert "sandbox ok" in res.stdout
    assert res.exit_code == 0
    assert res.timed_out is False


def test_local_sandbox_timeout(tmp_path: Path):
    sandbox = LocalSandbox(working_dir=tmp_path, default_timeout=1)

    # Command that exceeds timeout
    res = sandbox.execute("python -c \"import time; time.sleep(4)\"", timeout=1)
    assert res.is_success is False
    assert res.timed_out is True
    assert res.exit_code == 124
