"""Git inspection and diff tools."""

from typing import Any, Dict
from terminal_agent.git.adapter import GitAdapter
from terminal_agent.tools.base import BaseTool, ToolResult


class GitStatusTool(BaseTool):
    name = "git_status"
    description = "Get current git status including modified, untracked, and staged files. Requires a reason."
    parameters_schema = {
        "type": "object",
        "properties": {
            "reason": {"type": "string", "description": "Explainability reason for checking git status"}
        },
        "required": ["reason"]
    }

    def __init__(self, git_adapter: GitAdapter):
        self.git_adapter = git_adapter

    def run(self, args: Dict[str, Any], reason: str = "") -> ToolResult:
        status = self.git_adapter.get_status()
        if not status.is_repo:
            return ToolResult(
                success=True,
                output="Not a git repository.",
                data={"is_repo": False},
                reason=reason
            )

        summary = [
            f"Branch: {status.branch}",
            f"Clean: {status.is_clean}",
            f"Modified ({len(status.modified_files)}): {', '.join(status.modified_files) if status.modified_files else 'None'}",
            f"Untracked ({len(status.untracked_files)}): {', '.join(status.untracked_files) if status.untracked_files else 'None'}",
            f"Staged ({len(status.staged_files)}): {', '.join(status.staged_files) if status.staged_files else 'None'}",
        ]

        return ToolResult(
            success=True,
            output="\n".join(summary),
            data={
                "branch": status.branch,
                "is_clean": status.is_clean,
                "modified": status.modified_files,
                "untracked": status.untracked_files,
                "staged": status.staged_files
            },
            reason=reason
        )


class GitDiffTool(BaseTool):
    name = "git_diff"
    description = "View uncommitted git diff or stat summary. Requires a reason."
    parameters_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Optional specific file path to diff"},
            "stat": {"type": "boolean", "description": "Whether to return stat summary only"},
            "reason": {"type": "string", "description": "Explainability reason for viewing diff"}
        },
        "required": ["reason"]
    }

    def __init__(self, git_adapter: GitAdapter):
        self.git_adapter = git_adapter

    def run(self, args: Dict[str, Any], reason: str = "") -> ToolResult:
        path = args.get("path")
        stat = args.get("stat", False)
        diff_text = self.git_adapter.get_diff(file_path=path, stat=stat)
        stats = self.git_adapter.get_diff_stats()

        if not diff_text.strip():
            diff_text = "(No working tree differences found)"

        return ToolResult(
            success=True,
            output=diff_text,
            data={
                "files_changed": stats.files_changed,
                "insertions": stats.insertions,
                "deletions": stats.deletions,
                "modified_files": stats.modified_files
            },
            reason=reason
        )


class GitLogTool(BaseTool):
    name = "git_log"
    description = "View recent git commit history. Requires a reason."
    parameters_schema = {
        "type": "object",
        "properties": {
            "max_count": {"type": "integer", "description": "Maximum number of commits to show (default 5)"},
            "reason": {"type": "string", "description": "Explainability reason for checking git log"}
        },
        "required": ["reason"]
    }

    def __init__(self, git_adapter: GitAdapter):
        self.git_adapter = git_adapter

    def run(self, args: Dict[str, Any], reason: str = "") -> ToolResult:
        max_count = args.get("max_count", 5)
        commits = self.git_adapter.get_log(max_count=max_count)

        if not commits:
            return ToolResult(success=True, output="No commits found.", data={"commits": []}, reason=reason)

        lines = []
        for c in commits:
            lines.append(f"commit {c['hexsha']} - {c['author']} ({c['date'][:10]}): {c['message']}")

        return ToolResult(
            success=True,
            output="\n".join(lines),
            data={"commits": commits},
            reason=reason
        )

