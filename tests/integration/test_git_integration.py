"""Integration tests for git operations, status, diffs, and rollback."""

import subprocess
from pathlib import Path
import pytest
from terminal_agent.git.adapter import GitAdapter


def test_git_adapter(tmp_path: Path):
    # Initialize real git repo in temp dir
    subprocess.run(["git", "init"], cwd=str(tmp_path), check=True, stdout=subprocess.PIPE)
    subprocess.run(["git", "config", "user.name", "AgentTest"], cwd=str(tmp_path), check=True)
    subprocess.run(["git", "config", "user.email", "agent@test.local"], cwd=str(tmp_path), check=True)

    adapter = GitAdapter(tmp_path)
    assert adapter.is_git_repo() is True

    # Create and commit initial file
    f1 = tmp_path / "hello.py"
    f1.write_text("print('version 1')\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=str(tmp_path), check=True)
    subprocess.run(["git", "commit", "-m", "initial commit"], cwd=str(tmp_path), check=True)

    status1 = adapter.get_status()
    assert status1.is_clean is True

    # Modify file
    f1.write_text("print('version 2 modified')\n", encoding="utf-8")
    diff_stats = adapter.get_diff_stats()
    assert diff_stats.files_changed == 1
    assert "hello.py" in diff_stats.modified_files

    diff_text = adapter.get_diff()
    assert "+print('version 2 modified')" in diff_text

    # Test working tree restore
    adapter.restore_working_tree()
    assert f1.read_text() == "print('version 1')\n"
