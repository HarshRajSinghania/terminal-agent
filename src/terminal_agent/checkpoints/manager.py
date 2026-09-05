"""Checkpoint manager for creating and restoring repository and session snapshots."""

import json
import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from terminal_agent.git.adapter import GitAdapter
from terminal_agent.session.models import CheckpointSnapshot


def get_checkpoints_dir(working_dir: Optional[Path] = None) -> Path:
    """Return .terminal_agent/checkpoints directory."""
    base = working_dir or Path.cwd()
    c_dir = base / ".terminal_agent" / "checkpoints"
    c_dir.mkdir(parents=True, exist_ok=True)
    return c_dir


class CheckpointManager:
    """Creates, lists, and restores filesystem snapshots."""

    def __init__(self, working_dir: Optional[Path] = None):
        self.working_dir = (working_dir or Path.cwd()).resolve()
        self.checkpoints_dir = get_checkpoints_dir(self.working_dir)
        self.git_adapter = GitAdapter(self.working_dir)

    def create_checkpoint(
        self,
        name: str,
        step_number: int = 0,
        target_files: Optional[List[str]] = None
    ) -> CheckpointSnapshot:
        """Create a checkpoint snapshot of the repository."""
        chk_id = f"chk_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:4]}"
        chk_dir = self.checkpoints_dir / chk_id
        chk_dir.mkdir(parents=True, exist_ok=True)
        files_store_dir = chk_dir / "files"
        files_store_dir.mkdir(parents=True, exist_ok=True)

        git_commit = self.git_adapter.get_head_commit()

        # Determine which files to snapshot
        files_to_save: List[Path] = []
        if target_files:
            for f in target_files:
                p = (self.working_dir / f).resolve()
                if p.exists() and p.is_file():
                    files_to_save.append(p)
        else:
            # Snapshot all tracked and modified files in repository
            for root, dirs, files in os.walk(self.working_dir):
                dirs[:] = [d for d in dirs if d not in (".git", ".terminal_agent", ".venv", "venv", "__pycache__", "node_modules", "dist", "build", ".pytest_cache")]
                for f in files:
                    full_p = Path(root) / f
                    # Skip secret files
                    if not full_p.name.startswith(".env") and not full_p.name.endswith((".key", ".pem")):
                        files_to_save.append(full_p)

        file_contents: Dict[str, str] = {}
        modified_rel_paths: List[str] = []

        for p in files_to_save:
            try:
                rel_p = str(p.relative_to(self.working_dir)).replace("\\", "/")
                # Store copy in checkpoint dir
                dest = files_store_dir / rel_p
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(p, dest)

                # Store text content if valid text file
                try:
                    content = p.read_text(encoding="utf-8", errors="ignore")
                    if len(content) < 500000: # Limit memory footprint
                        file_contents[rel_p] = content
                except Exception:
                    pass

                modified_rel_paths.append(rel_p)
            except Exception:
                continue

        snapshot = CheckpointSnapshot(
            checkpoint_id=chk_id,
            name=name,
            created_at=datetime.utcnow().isoformat(),
            step_number=step_number,
            git_commit=git_commit,
            modified_files=modified_rel_paths,
            file_contents=file_contents
        )

        metadata_file = chk_dir / "metadata.json"
        metadata_file.write_text(snapshot.model_dump_json(indent=2), encoding="utf-8")
        return snapshot

    def list_checkpoints(self) -> List[CheckpointSnapshot]:
        """List all available checkpoints ordered by most recent."""
        checkpoints = []
        if not self.checkpoints_dir.exists():
            return checkpoints

        for d in sorted(self.checkpoints_dir.iterdir(), key=os.path.getmtime, reverse=True):
            if d.is_dir():
                meta_file = d / "metadata.json"
                if meta_file.exists():
                    try:
                        data = json.loads(meta_file.read_text(encoding="utf-8"))
                        checkpoints.append(CheckpointSnapshot.model_validate(data))
                    except Exception:
                        continue
        return checkpoints

    def get_checkpoint(self, checkpoint_id: str) -> Optional[CheckpointSnapshot]:
        """Retrieve checkpoint by ID or name substring."""
        for chk in self.list_checkpoints():
            if chk.checkpoint_id == checkpoint_id or checkpoint_id in chk.checkpoint_id or chk.name == checkpoint_id:
                return chk
        return None

    def rollback(self, checkpoint_id: str) -> bool:
        """Restore repository state from a checkpoint."""
        chk = self.get_checkpoint(checkpoint_id)
        if not chk:
            return False

        chk_dir = self.checkpoints_dir / chk.checkpoint_id
        files_store_dir = chk_dir / "files"

        if not files_store_dir.exists():
            return False

        # Restore files from snapshot
        for root, _, files in os.walk(files_store_dir):
            for f in files:
                src_path = Path(root) / f
                rel_path = src_path.relative_to(files_store_dir)
                target_path = self.working_dir / rel_path
                target_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_path, target_path)

        return True
