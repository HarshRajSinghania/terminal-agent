"""CLI checkpoint and rollback commands."""

from pathlib import Path
from typing import Optional
import typer
from rich.table import Table

from terminal_agent.checkpoints.manager import CheckpointManager
from terminal_agent.cli.theme import SYM_CHECK, SYM_CROSS, console
from terminal_agent.cli.ui import render_header

checkpoint_app = typer.Typer(help="Manage repository checkpoints.")


@checkpoint_app.command("list")
def list_checkpoints_cmd(
    working_dir: Optional[Path] = typer.Option(None, "--cwd", "-C", help="Target repository directory"),
) -> None:
    """List all available checkpoints for this repository."""
    render_header()
    target_dir = (working_dir or Path.cwd()).resolve()
    mgr = CheckpointManager(target_dir)
    checkpoints = mgr.list_checkpoints()

    if not checkpoints:
        console.print("[agent.muted]No checkpoints found for this repository.[/agent.muted]")
        return

    table = Table(title="[agent.accent]CHECKPOINTS[/agent.accent]", border_style="agent.border")
    table.add_column("Checkpoint ID", style="agent.accent")
    table.add_column("Name", style="agent.text")
    table.add_column("Created At", style="agent.muted")
    table.add_column("Files", style="agent.muted")
    table.add_column("Git Commit", style="agent.muted")

    for chk in checkpoints:
        table.add_row(
            chk.checkpoint_id,
            chk.name,
            chk.created_at[:19].replace("T", " "),
            str(len(chk.modified_files)),
            chk.git_commit[:8] if chk.git_commit else "N/A"
        )

    console.print(table)


@checkpoint_app.command("create")
def create_checkpoint_cmd(
    name: str = typer.Argument("manual_checkpoint", help="Descriptive checkpoint name"),
    working_dir: Optional[Path] = typer.Option(None, "--cwd", "-C", help="Target repository directory"),
) -> None:
    """Create a new manual checkpoint snapshot."""
    render_header()
    target_dir = (working_dir or Path.cwd()).resolve()
    mgr = CheckpointManager(target_dir)
    snapshot = mgr.create_checkpoint(name=name)
    console.print(f"{SYM_CHECK} [agent.success]Created checkpoint '{snapshot.checkpoint_id}' ('{snapshot.name}') with {len(snapshot.modified_files)} files.[/agent.success]")


def rollback_command(
    checkpoint_id: str = typer.Argument(..., help="Checkpoint ID or name to restore"),
    working_dir: Optional[Path] = typer.Option(None, "--cwd", "-C", help="Target repository directory"),
) -> None:
    """Roll back workspace files to a previous checkpoint."""
    render_header()
    target_dir = (working_dir or Path.cwd()).resolve()
    mgr = CheckpointManager(target_dir)
    success = mgr.rollback(checkpoint_id)

    if success:
        console.print(f"{SYM_CHECK} [agent.success]Successfully rolled back to checkpoint '{checkpoint_id}'.[/agent.success]")
    else:
        console.print(f"{SYM_CROSS} [agent.error]Failed to rollback to checkpoint '{checkpoint_id}'. Checkpoint not found.[/agent.error]")
        raise typer.Exit(1)
