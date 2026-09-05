"""File reading, writing, editing, and listing tools."""

import os
from pathlib import Path
from typing import Any, Dict, Optional

from terminal_agent.security.secrets import SecretGuard
from terminal_agent.tools.base import BaseTool, ToolResult


class ReadFileTool(BaseTool):
    name = "read_file"
    description = "Read file contents with optional line range. Requires a reason explaining why you are inspecting the file."
    parameters_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Relative file path"},
            "start_line": {"type": "integer", "description": "1-indexed starting line number (optional)"},
            "end_line": {"type": "integer", "description": "1-indexed ending line number (optional)"},
            "reason": {"type": "string", "description": "Explainability reason for reading this file"}
        },
        "required": ["path", "reason"]
    }

    def __init__(self, root_dir: Path, secret_guard: SecretGuard):
        self.root_dir = root_dir
        self.secret_guard = secret_guard

    def run(self, args: Dict[str, Any], reason: str = "") -> ToolResult:
        rel_path = args.get("path", "")
        full_path = (self.root_dir / rel_path).resolve()

        if self.secret_guard.is_path_blocked(full_path):
            return ToolResult(
                success=False,
                output="",
                error=f"Access to '{rel_path}' is blocked by security policy.",
                reason=reason
            )

        if not full_path.exists() or not full_path.is_file():
            return ToolResult(
                success=False,
                output="",
                error=f"File '{rel_path}' does not exist.",
                reason=reason
            )

        try:
            content = full_path.read_text(encoding="utf-8", errors="replace")
            lines = content.splitlines()
            total_lines = len(lines)

            start = max(1, args.get("start_line", 1)) - 1
            end = min(total_lines, args.get("end_line", total_lines))

            selected_lines = lines[start:end]
            formatted = [f"{i+1+start:4d} | {line}" for i, line in enumerate(selected_lines)]
            output_str = f"File: {rel_path} (lines {start+1}-{end} of {total_lines})\n" + "\n".join(formatted)

            return ToolResult(
                success=True,
                output=output_str,
                data={"total_lines": total_lines, "lines_returned": len(selected_lines), "path": rel_path},
                reason=reason
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Failed to read file: {e}",
                reason=reason
            )


class WriteFileTool(BaseTool):
    name = "write_file"
    description = "Create or overwrite a file with full content. Requires a reason explaining the change."
    parameters_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Relative file path to write"},
            "content": {"type": "string", "description": "Full file content to write"},
            "reason": {"type": "string", "description": "Explainability reason for writing this file"}
        },
        "required": ["path", "content", "reason"]
    }

    def __init__(self, root_dir: Path, secret_guard: SecretGuard):
        self.root_dir = root_dir
        self.secret_guard = secret_guard

    def run(self, args: Dict[str, Any], reason: str = "") -> ToolResult:
        rel_path = args.get("path", "")
        content = args.get("content", "")
        full_path = (self.root_dir / rel_path).resolve()

        if self.secret_guard.is_path_blocked(full_path):
            return ToolResult(
                success=False,
                output="",
                error=f"Writing to '{rel_path}' is blocked by security policy.",
                reason=reason
            )

        try:
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding="utf-8")
            line_count = len(content.splitlines())
            return ToolResult(
                success=True,
                output=f"Successfully wrote {line_count} lines to {rel_path}",
                data={"path": rel_path, "bytes_written": len(content.encode("utf-8")), "line_count": line_count},
                reason=reason
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Failed to write file: {e}",
                reason=reason
            )


class EditFileTool(BaseTool):
    name = "edit_file"
    description = "Edit an existing file by replacing target content with replacement content. Requires an explicit reason."
    parameters_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Relative file path to edit"},
            "old_str": {"type": "string", "description": "The exact existing text snippet to replace"},
            "new_str": {"type": "string", "description": "The new replacement text"},
            "reason": {"type": "string", "description": "Explainability reason for making this edit"}
        },
        "required": ["path", "old_str", "new_str", "reason"]
    }

    def __init__(self, root_dir: Path, secret_guard: SecretGuard):
        self.root_dir = root_dir
        self.secret_guard = secret_guard

    def run(self, args: Dict[str, Any], reason: str = "") -> ToolResult:
        rel_path = args.get("path", "")
        old_str = args.get("old_str", "")
        new_str = args.get("new_str", "")
        full_path = (self.root_dir / rel_path).resolve()

        if self.secret_guard.is_path_blocked(full_path):
            return ToolResult(
                success=False,
                output="",
                error=f"Editing '{rel_path}' is blocked by security policy.",
                reason=reason
            )

        if not full_path.exists() or not full_path.is_file():
            return ToolResult(
                success=False,
                output="",
                error=f"File '{rel_path}' does not exist.",
                reason=reason
            )

        try:
            content = full_path.read_text(encoding="utf-8")
            if old_str not in content:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Target snippet not found in {rel_path}. Make sure whitespace and line breaks match exactly.",
                    reason=reason
                )

            count = content.count(old_str)
            if count > 1:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Target snippet matches {count} locations in {rel_path}. Please provide a more unique snippet.",
                    reason=reason
                )

            new_content = content.replace(old_str, new_str, 1)
            full_path.write_text(new_content, encoding="utf-8")

            return ToolResult(
                success=True,
                output=f"Successfully applied edit to {rel_path}",
                data={"path": rel_path},
                reason=reason
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Failed to edit file: {e}",
                reason=reason
            )


class ListFilesTool(BaseTool):
    name = "list_files"
    description = "List files and directories within a target directory. Requires a reason."
    parameters_schema = {
        "type": "object",
        "properties": {
            "directory": {"type": "string", "description": "Relative directory path (defaults to root .)"},
            "recursive": {"type": "boolean", "description": "Whether to list recursively"},
            "reason": {"type": "string", "description": "Explainability reason for listing files"}
        },
        "required": ["reason"]
    }

    def __init__(self, root_dir: Path, secret_guard: SecretGuard):
        self.root_dir = root_dir
        self.secret_guard = secret_guard

    def run(self, args: Dict[str, Any], reason: str = "") -> ToolResult:
        dir_rel = args.get("directory", ".") or "."
        recursive = args.get("recursive", False)
        target_dir = (self.root_dir / dir_rel).resolve()

        if self.secret_guard.is_path_blocked(target_dir):
            return ToolResult(
                success=False,
                output="",
                error=f"Directory '{dir_rel}' is blocked by security policy.",
                reason=reason
            )

        if not target_dir.exists() or not target_dir.is_dir():
            return ToolResult(
                success=False,
                output="",
                error=f"Directory '{dir_rel}' does not exist.",
                reason=reason
            )

        try:
            results = []
            if recursive:
                for root, dirs, files in os.walk(target_dir):
                    dirs[:] = [d for d in dirs if d not in (".git", ".terminal_agent", ".venv", "venv", "__pycache__")]
                    for f in sorted(files):
                        p = Path(root) / f
                        if not self.secret_guard.is_path_blocked(p):
                            results.append(str(p.relative_to(self.root_dir)).replace("\\", "/"))
            else:
                for item in sorted(target_dir.iterdir()):
                    if not self.secret_guard.is_path_blocked(item):
                        name = item.name + ("/" if item.is_dir() else "")
                        results.append(name)

            out_text = f"Contents of {dir_rel}:\n" + "\n".join(f"- {r}" for r in results[:100])
            if len(results) > 100:
                out_text += f"\n... ({len(results) - 100} more items truncated)"

            return ToolResult(
                success=True,
                output=out_text,
                data={"count": len(results), "items": results[:100]},
                reason=reason
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Failed to list directory: {e}",
                reason=reason
            )


class SearchFilesTool(BaseTool):
    name = "search_files"
    description = "Search for a keyword or regex pattern in the workspace files. Requires a reason."
    parameters_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search pattern or keyword"},
            "directory": {"type": "string", "description": "Optional subdirectory to restrict search"},
            "reason": {"type": "string", "description": "Explainability reason for searching files"}
        },
        "required": ["query", "reason"]
    }

    def __init__(self, root_dir: Path, secret_guard: SecretGuard):
        self.root_dir = root_dir
        self.secret_guard = secret_guard

    def run(self, args: Dict[str, Any], reason: str = "") -> ToolResult:
        query = args.get("query", "")
        dir_rel = args.get("directory", ".") or "."
        target_dir = (self.root_dir / dir_rel).resolve()

        if not query:
            return ToolResult(success=False, output="", error="Query cannot be empty", reason=reason)

        matches = []
        try:
            for root, dirs, files in os.walk(target_dir):
                dirs[:] = [d for d in dirs if d not in (".git", ".terminal_agent", ".venv", "venv", "__pycache__", "node_modules")]
                for f in sorted(files):
                    p = Path(root) / f
                    if self.secret_guard.is_path_blocked(p):
                        continue
                    if p.stat().st_size > 300_000:
                        continue
                    try:
                        content = p.read_text(encoding="utf-8", errors="ignore")
                        rel_path = str(p.relative_to(self.root_dir)).replace("\\", "/")
                        for line_no, line in enumerate(content.splitlines(), start=1):
                            if query.lower() in line.lower():
                                matches.append(f"{rel_path}:{line_no}: {line.strip()[:150]}")
                                if len(matches) >= 50:
                                    break
                    except Exception:
                        continue
                if len(matches) >= 50:
                    break

            if matches:
                output_str = f"Found {len(matches)} matches for '{query}':\n" + "\n".join(matches)
            else:
                output_str = f"No matches found for '{query}' in {dir_rel}"

            return ToolResult(
                success=True,
                output=output_str,
                data={"query": query, "matches_count": len(matches)},
                reason=reason
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Failed search: {e}",
                reason=reason
            )

