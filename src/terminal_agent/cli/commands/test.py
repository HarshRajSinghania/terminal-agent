"""CLI test command running independent verification suite."""

from pathlib import Path
from typing import Optional
import typer

from terminal_agent.cli.theme import console
from terminal_agent.cli.ui import render_header, render_verification_result
from terminal_agent.config.settings import load_config
from terminal_agent.git.adapter import GitAdapter
from terminal_agent.sandbox.local import LocalSandbox
from terminal_agent.security.secrets import SecretGuard
from terminal_agent.session.models import VerificationStatus
from terminal_agent.verifier.engine import IndependentVerifier


def test_command(
    test_cmd: Optional[str] = typer.Option(None, "--cmd", "-c", help="Custom test command override"),
    working_dir: Optional[Path] = typer.Option(None, "--cwd", "-C", help="Target repository directory"),
) -> None:
    """Run independent verification test suite on current workspace."""
    render_header()
    target_dir = (working_dir or Path.cwd()).resolve()

    config = load_config(target_dir / "terminal-agent.config.yaml")
    secret_guard = SecretGuard(blocked_patterns=config.security.blocked_paths, working_dir=target_dir)
    sandbox = LocalSandbox(working_dir=target_dir, default_timeout=config.sandbox.timeout_seconds, secret_guard=secret_guard)
    git_adapter = GitAdapter(target_dir)

    verifier = IndependentVerifier(sandbox, git_adapter, config.verification, target_dir)

    console.print(f"[agent.muted]Running independent verification in {target_dir}...[/agent.muted]\n")
    result = verifier.verify(custom_test_cmd=test_cmd)
    render_verification_result(result)

    if result.status != VerificationStatus.VERIFIED:
        raise typer.Exit(1)

