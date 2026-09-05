"""CLI trace command inspecting telemetry event streams."""

from pathlib import Path
from typing import Optional
import typer
from rich.table import Table

from terminal_agent.cli.theme import SYM_CHECK, SYM_CROSS, console
from terminal_agent.cli.ui import render_header
from terminal_agent.session.manager import SessionManager
from terminal_agent.telemetry.events import TelemetryLogger


def trace_command(
    session_id: Optional[str] = typer.Argument(None, help="Session ID to inspect (defaults to latest)"),
    working_dir: Optional[Path] = typer.Option(None, "--cwd", "-C", help="Target repository directory"),
) -> None:
    """Inspect structured telemetry event trace of an agent session."""
    render_header()
    target_dir = (working_dir or Path.cwd()).resolve()

    if not session_id:
        session_mgr = SessionManager(target_dir)
        latest = session_mgr.get_latest_session()
        if latest:
            session_id = latest.session_id
        else:
            console.print("[agent.error]No active or past sessions found.[/agent.error]")
            raise typer.Exit(1)

    events = TelemetryLogger.read_trace(session_id, working_dir=target_dir)

    if not events:
        console.print(f"[agent.muted]No trace events recorded for session '{session_id}'.[/agent.muted]")
        return

    table = Table(title=f"[agent.accent]TELEMETRY TRACE: {session_id}[/agent.accent]", border_style="agent.border")
    table.add_column("Time", style="agent.muted")
    table.add_column("Step", style="agent.accent", width=6)
    table.add_column("Event", style="agent.text", width=14)
    table.add_column("Tool", style="agent.accent", width=16)
    table.add_column("Status", width=8)
    table.add_column("Duration", style="agent.muted", width=10)
    table.add_column("Reason / Context", style="agent.text")

    for ev in events:
        time_str = ev.timestamp[11:19]
        status_sym = SYM_CHECK if ev.status == "success" else SYM_CROSS
        table.add_row(
            time_str,
            str(ev.step),
            ev.event_type,
            ev.tool or "-",
            status_sym,
            f"{ev.duration_ms}ms",
            ev.reason or "-"
        )

    console.print(table)
