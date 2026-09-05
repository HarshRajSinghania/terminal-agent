"""CLI status command inspecting active repository and latest session state."""

from pathlib import Path
from typing import Optional
import typer
from rich.panel import Panel
from rich.table import Table

from terminal_agent.cli.theme import SYM_CHECK, SYM_CROSS, console
from terminal_agent.cli.ui import render_header, render_plan, render_task_card
from terminal_agent.git.adapter import GitAdapter
from terminal_agent.session.manager import SessionManager


def status_command(
    working_dir: Optional[Path] = typer.Option(None, "--cwd", "-C", help="Target repository directory"),
) -> None:
    """Inspect repository status and latest agent session."""
    render_header()
    target_dir = (working_dir or Path.cwd()).resolve()

    # Git Status
    git_adapter = GitAdapter(target_dir)
    status = git_adapter.get_status()
    diff_stats = git_adapter.get_diff_stats()

    t_git = Table(box=None, show_header=False)
    t_git.add_column(style="agent.muted", width=16)
    t_git.add_column(style="agent.text")

    t_git.add_row("GIT REPO", "[agent.success]Yes[/agent.success]" if status.is_repo else "[agent.muted]No[/agent.muted]")
    if status.is_repo:
        t_git.add_row("BRANCH", status.branch)
        t_git.add_row("WORKING TREE", "[agent.success]Clean[/agent.success]" if status.is_clean else "[agent.warning]Modified[/agent.warning]")
        t_git.add_row("MODIFIED FILES", f"{len(status.modified_files)} ({', '.join(status.modified_files) if status.modified_files else 'None'})")
        t_git.add_row("UNTRACKED FILES", f"{len(status.untracked_files)} ({', '.join(status.untracked_files) if status.untracked_files else 'None'})")
        t_git.add_row("DIFF STATS", f"+{diff_stats.insertions} / -{diff_stats.deletions} lines across {diff_stats.files_changed} files")

    console.print(Panel(t_git, title="[agent.accent]REPOSITORY STATUS[/agent.accent]", border_style="agent.border"))

    # Session Status
    session_mgr = SessionManager(target_dir)
    latest = session_mgr.get_latest_session()

    if latest:
        t_sess = Table(box=None, show_header=False)
        t_sess.add_column(style="agent.muted", width=16)
        t_sess.add_column(style="agent.text")

        t_sess.add_row("SESSION ID", latest.session_id)
        t_sess.add_row("STATUS", f"[agent.accent]{latest.current_status.value}[/agent.accent]")
        t_sess.add_row("TASK", latest.task_description)
        t_sess.add_row("STEPS COMPLETED", str(len(latest.completed_steps)))
        t_sess.add_row("RETRIES", str(len(latest.failures)))
        t_sess.add_row("LAST UPDATED", latest.updated_at)

        console.print(Panel(t_sess, title="[agent.accent]LATEST AGENT SESSION[/agent.accent]", border_style="agent.border"))
        if latest.plan:
            render_plan(latest.plan)
    else:
        console.print("[agent.muted]No previous agent sessions recorded in this workspace.[/agent.muted]")

