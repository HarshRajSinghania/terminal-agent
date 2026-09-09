"""Git operations adapter using GitPython and git CLI fallback."""

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional
import git


@dataclass
class GitDiffStat:
    files_changed: int
    insertions: int
    deletions: int
    modified_files: List[str]


@dataclass
class GitStatusResult:
    is_repo: bool
    branch: str
    is_clean: bool
    modified_files: List[str]
    untracked_files: List[str]
    deleted_files: List[str]
    staged_files: List[str]


class GitAdapter:
    """Provides git inspection, diff analysis, and safe rollback helpers."""

    def __init__(self, repo_dir: Optional[Path] = None):
        self.repo_dir = (repo_dir or Path.cwd()).resolve()

    def is_git_repo(self) -> bool:
        """Check if working directory is a git repository."""
        try:
            _ = git.Repo(self.repo_dir, search_parent_directories=True)
            return True
        except Exception:
            return False

    def get_repo(self) -> Optional[git.Repo]:
        """Get git.Repo instance."""
        try:
            return git.Repo(self.repo_dir, search_parent_directories=True)
        except Exception:
            return None

    def get_status(self) -> GitStatusResult:
        """Inspect repository status."""
        repo = self.get_repo()
        if not repo:
            return GitStatusResult(
                is_repo=False,
                branch="",
                is_clean=True,
                modified_files=[],
                untracked_files=[],
                deleted_files=[],
                staged_files=[]
            )

        try:
            try:
                branch = repo.active_branch.name
            except Exception:
                branch = "DETACHED"

            IGNORE_PREFIXES = (
                ".terminal_agent",
                ".pytest_cache",
                "__pycache__",
                ".hypothesis",
                ".coverage",
                ".tmp",
                ".tox",
                ".mypy_cache",
                ".ruff_cache",
            )

            def is_relevant(path: str) -> bool:
                p_norm = path.replace("\\", "/").strip("/")
                filename = Path(p_norm).name
                if (
                    filename.startswith(".coverage")
                    or filename == ".coverage"
                    or p_norm.endswith(".pyc")
                    or p_norm.endswith(".pyo")
                    or p_norm.endswith(".pyd")
                ):
                    return False
                for ign in IGNORE_PREFIXES:
                    if p_norm == ign or p_norm.startswith(f"{ign}/") or f"/{ign}/" in p_norm or p_norm.endswith(f"/{ign}"):
                        return False
                return True

            modified = [item.a_path for item in repo.index.diff(None) if is_relevant(item.a_path)]
            untracked = [p for p in repo.untracked_files if is_relevant(p)]
            deleted = [item.a_path for item in repo.index.diff(None) if item.deleted_file and is_relevant(item.a_path)]
            
            try:
                staged = [item.a_path for item in repo.head.commit.diff() if is_relevant(item.a_path)]
            except Exception:
                staged = []

            is_clean = len(modified) == 0 and len(untracked) == 0 and len(staged) == 0

            return GitStatusResult(
                is_repo=True,
                branch=branch,
                is_clean=is_clean,
                modified_files=modified,
                untracked_files=untracked,
                deleted_files=deleted,
                staged_files=staged
            )
        except Exception:
            return GitStatusResult(
                is_repo=True,
                branch="unknown",
                is_clean=True,
                modified_files=[],
                untracked_files=[],
                deleted_files=[],
                staged_files=[]
            )

    def get_diff(self, file_path: Optional[str] = None, stat: bool = False) -> str:
        """Get git diff output."""
        if not self.is_git_repo():
            return ""

        cmd = ["git", "diff"]
        if stat:
            cmd.append("--stat")
        if file_path:
            cmd.extend(["--", file_path])

        try:
            res = subprocess.run(
                cmd,
                cwd=str(self.repo_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=15
            )
            return res.stdout
        except Exception as e:
            return f"Error computing diff: {e}"

    def get_diff_stats(self) -> GitDiffStat:
        """Calculate number of files changed, insertions, deletions, and changed paths."""
        status = self.get_status()
        if not status.is_repo:
            return GitDiffStat(files_changed=0, insertions=0, deletions=0, modified_files=[])

        all_changed = list(set(status.modified_files + status.untracked_files + status.staged_files))
        
        diff_text = self.get_diff()
        insertions = 0
        deletions = 0

        for line in diff_text.splitlines():
            if line.startswith("+") and not line.startswith("+++"):
                insertions += 1
            elif line.startswith("-") and not line.startswith("---"):
                deletions += 1

        return GitDiffStat(
            files_changed=len(all_changed),
            insertions=insertions,
            deletions=deletions,
            modified_files=sorted(all_changed)
        )

    def get_log(self, max_count: int = 10) -> List[Dict[str, str]]:
        """Get recent git commits."""
        repo = self.get_repo()
        if not repo:
            return []

        commits = []
        try:
            for commit in repo.iter_commits(max_count=max_count):
                commits.append({
                    "hexsha": commit.hexsha[:8],
                    "author": str(commit.author),
                    "date": commit.committed_datetime.isoformat(),
                    "message": commit.message.strip()
                })
        except Exception:
            pass
        return commits

    def get_head_commit(self) -> Optional[str]:
        """Return head commit hexsha or None."""
        repo = self.get_repo()
        if not repo:
            return None
        try:
            return repo.head.commit.hexsha
        except Exception:
            return None

    def restore_working_tree(self) -> bool:
        """Discard unstaged changes safely."""
        if not self.is_git_repo():
            return False
        try:
            subprocess.run(["git", "checkout", "--", "."], cwd=str(self.repo_dir), check=True)
            return True
        except Exception:
            return False
