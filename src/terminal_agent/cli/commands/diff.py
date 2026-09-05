"""CLI diff command displaying repository changes and stats."""

from pathlib import Path
from typing import Optional
import typer
from rich.panel import Panel
from rich.syntax import Syntax

from terminal_agent.cli.theme import console
from terminal_agent.cli.ui import render_header
from terminal_agent.git.adapter import GitAdapter


def diff_command(
    file_path: Optional[str] = typer.Argument(None, help="Specific file path to diff"),
    stat_only: bool = typer.Option(False, "--stat", "-s", help="Show diffstat summary only"),
    working_dir: Optional[Path] = typer.Option(None, "--cwd", "-C", help="Target repository directory"),
) -> None:
    """View current git diff and changes made by agent."""
    render_header()
    target_dir = (working_dir or Path.cwd()).resolve()
    git_adapter = GitAdapter(target_dir)

    if not git_adapter.is_git_repo():
        console.print("[agent.error]Current directory is not a Git repository.[/agent.error]")
        raise typer.Exit(1)

    diff_stats = git_adapter.get_diff_stats()
    diff_text = git_adapter.get_diff(file_path=file_path, stat=stat_only)

    console.print(
        f"[agent.accent]Changed Files ({diff_stats.files_changed}):[/agent.accent] "
        f"[agent.success]+{diff_stats.insertions}[/agent.success] / [agent.error]-{diff_stats.deletions}[/agent.error] lines\n"
    )

    if not diff_text.strip():
        console.print("[agent.muted]No working tree modifications.[/agent.muted]")
        return

    if stat_only:
        console.print(Panel(diff_text, title="[agent.accent]DIFF STAT[/agent.accent]", border_style="agent.border"))
    else:
        syntax = Syntax(diff_text, "diff", theme="monokai", line_numbers=False)
        console.print(Panel(syntax, title="[agent.accent]WORKING TREE DIFF[/agent.accent]", border_style="agent.border"))
