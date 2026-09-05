"""Deterministic context retrieval engine for codebase exploration."""

import fnmatch
import os
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from terminal_agent.context.ranker import DeterministicRanker, tokenize
from terminal_agent.git.adapter import GitAdapter
from terminal_agent.security.secrets import SecretGuard
from terminal_agent.session.models import TaskContract


IGNORE_PATTERNS = {
    ".git", ".terminal_agent", ".venv", "venv", "__pycache__",
    ".pytest_cache", ".coverage", "htmlcov", "dist", "build",
    "node_modules", ".idea", ".vscode", "*.pyc", "*.pyo", "*.egg-info"
}


class RepositoryContextEngine:
    """Explores repository structure and extracts deterministic, token-efficient context."""

    def __init__(self, root_dir: Optional[Path] = None, secret_guard: Optional[SecretGuard] = None):
        self.root_dir = (root_dir or Path.cwd()).resolve()
        self.secret_guard = secret_guard or SecretGuard(working_dir=self.root_dir)
        self.git_adapter = GitAdapter(self.root_dir)

    def is_ignored(self, path: Path) -> bool:
        """Check if path matches standard ignore patterns or security blocklist."""
        if self.secret_guard.is_path_blocked(path):
            return True

        parts = path.parts
        for part in parts:
            if part in IGNORE_PATTERNS:
                return True
            for pat in IGNORE_PATTERNS:
                if fnmatch.fnmatch(part, pat):
                    return True
        return False

    def list_all_files(self, max_files: int = 500) -> List[Path]:
        """Discover all valid non-ignored repository files."""
        collected = []
        for root, dirs, files in os.walk(self.root_dir):
            # Prune ignored directories in-place
            dirs[:] = [
                d for d in dirs
                if d not in IGNORE_PATTERNS and not any(fnmatch.fnmatch(d, p) for p in IGNORE_PATTERNS)
            ]
            for f in files:
                p = Path(root) / f
                if not self.is_ignored(p):
                    collected.append(p)
                    if len(collected) >= max_files:
                        return collected
        return collected

    def build_tree_summary(self, max_depth: int = 3, max_entries: int = 60) -> str:
        """Generate a clean ASCII directory tree summary."""
        lines = [f"{self.root_dir.name}/"]
        count = 0

        def _traverse(current_dir: Path, prefix: str, depth: int):
            nonlocal count
            if depth > max_depth or count >= max_entries:
                return

            try:
                entries = sorted(list(current_dir.iterdir()), key=lambda x: (not x.is_dir(), x.name.lower()))
            except Exception:
                return

            valid_entries = [e for e in entries if not self.is_ignored(e)]
            total = len(valid_entries)

            for i, entry in enumerate(valid_entries):
                if count >= max_entries:
                    lines.append(f"{prefix}└── ... (truncated)")
                    break

                is_last = (i == total - 1)
                connector = "└── " if is_last else "├── "
                sub_prefix = "    " if is_last else "│   "

                if entry.is_dir():
                    lines.append(f"{prefix}{connector}{entry.name}/")
                    count += 1
                    _traverse(entry, prefix + sub_prefix, depth + 1)
                else:
                    lines.append(f"{prefix}{connector}{entry.name}")
                    count += 1

        _traverse(self.root_dir, "", 1)
        return "\n".join(lines)

    def search_relevant_files(self, query: str, top_k: int = 5) -> List[Tuple[str, float, str]]:
        """
        Rank repository files by relevance to query.
        Returns List of (relative_path, score, reason).
        """
        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        all_files = self.list_all_files()
        scored_files = []

        for p in all_files:
            try:
                # Only read text files up to 500KB
                if p.stat().st_size > 500_000:
                    continue
                content = p.read_text(encoding="utf-8", errors="ignore")
                score, reason = DeterministicRanker.score_file(p, content, query_tokens, self.root_dir)
                if score > 0.5:
                    rel_p = str(p.relative_to(self.root_dir)).replace("\\", "/")
                    scored_files.append((rel_p, score, reason))
            except Exception:
                continue

        scored_files.sort(key=lambda x: x[1], reverse=True)
        return scored_files[:top_k]

    def read_file_with_lines(self, rel_path: str, max_lines: int = 300) -> str:
        """Read file content with line numbers."""
        full_path = (self.root_dir / rel_path).resolve()
        if self.secret_guard.is_path_blocked(full_path):
            return f"[ERROR: Access to {rel_path} blocked by security policy]"
        if not full_path.exists():
            return f"[ERROR: File {rel_path} does not exist]"

        try:
            lines = full_path.read_text(encoding="utf-8", errors="replace").splitlines()
            numbered = [f"{i+1:4d} | {line}" for i, line in enumerate(lines[:max_lines])]
            if len(lines) > max_lines:
                numbered.append(f"... ({len(lines) - max_lines} more lines)")
            return "\n".join(numbered)
        except Exception as e:
            return f"[ERROR reading {rel_path}: {e}]"

    def build_initial_context(self, task_description: str, contract: Optional[TaskContract] = None) -> str:
        """Assemble structured, deterministic repository context for the model."""
        tree = self.build_tree_summary()
        relevant = self.search_relevant_files(task_description, top_k=5)

        context_parts = [
            f"=== REPOSITORY ROOT: {self.root_dir.name} ===",
            "=== DIRECTORY STRUCTURE ===",
            tree,
            "",
            "=== RELEVANT FILES IDENTIFIED ===",
        ]

        if relevant:
            for rel_path, score, reason in relevant:
                context_parts.append(f"- {rel_path} (Score: {score:.1f}, Matches: {reason})")
        else:
            context_parts.append("(No specific file matches identified from initial keywords)")

        # Include Git status if available
        status = self.git_adapter.get_status()
        if status.is_repo:
            context_parts.extend([
                "",
                f"=== GIT STATUS: Branch '{status.branch}' ===",
                f"Modified: {status.modified_files}",
                f"Untracked: {status.untracked_files}",
            ])

        return "\n".join(context_parts)

