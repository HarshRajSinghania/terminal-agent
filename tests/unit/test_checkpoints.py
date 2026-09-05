"""Unit tests for checkpoint creation and rollback."""

from pathlib import Path
from terminal_agent.checkpoints.manager import CheckpointManager


def test_checkpoint_and_rollback(tmp_path: Path):
    mgr = CheckpointManager(working_dir=tmp_path)
    file1 = tmp_path / "hello.py"
    file1.write_text("print('version 1')", encoding="utf-8")

    # Create baseline checkpoint
    chk = mgr.create_checkpoint(name="v1_baseline", step_number=1)
    assert chk.checkpoint_id.startswith("chk_")
    assert "hello.py" in chk.modified_files

    # Modify file
    file1.write_text("print('version 2 corrupted')", encoding="utf-8")
    assert file1.read_text() == "print('version 2 corrupted')"

    # Rollback to checkpoint
    success = mgr.rollback(chk.checkpoint_id)
    assert success is True
    assert file1.read_text() == "print('version 1')"


def test_list_checkpoints(tmp_path: Path):
    mgr = CheckpointManager(working_dir=tmp_path)
    (tmp_path / "test.txt").write_text("hello", encoding="utf-8")

    mgr.create_checkpoint(name="first")
    mgr.create_checkpoint(name="second")

    checkpoints = mgr.list_checkpoints()
    assert len(checkpoints) == 2

