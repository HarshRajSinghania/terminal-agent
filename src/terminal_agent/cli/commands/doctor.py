"""CLI doctor command checking environment, toolchain, and provider health."""

import os
import shutil
import sys
from pathlib import Path
from typing import Optional
import typer
from rich.table import Table

from terminal_agent.cli.theme import SYM_CHECK, SYM_CROSS, SYM_WARN, console
from terminal_agent.cli.ui import render_header
from terminal_agent.config.settings import load_config
from terminal_agent.git.adapter import GitAdapter
from terminal_agent.providers.factory import create_provider
from terminal_agent.sandbox.docker import DockerSandbox


def doctor_command(
    working_dir: Optional[Path] = typer.Option(None, "--cwd", "-C", help="Target repository directory"),
) -> None:
    """Check system toolchains, sandbox prerequisites, and model availability."""
    render_header()
    target_dir = (working_dir or Path.cwd()).resolve()
    config = load_config(target_dir / "terminal-agent.config.yaml")

    console.print("[agent.accent]Running system diagnostics...[/agent.accent]\n")

    table = Table(title="[agent.accent]SYSTEM HEALTH REPORT[/agent.accent]", border_style="agent.border")
    table.add_column("Component", style="agent.text", width=24)
    table.add_column("Status", width=12)
    table.add_column("Details", style="agent.muted")

    # 1. Python Check
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    if sys.version_info >= (3, 11):
        table.add_row("Python Version", SYM_CHECK, f"Python {py_ver}")
    else:
        table.add_row("Python Version", SYM_WARN, f"Python {py_ver} (Recommend 3.11+)")

    # 2. Git Check
    git_path = shutil.which("git")
    if git_path:
        git_adapter = GitAdapter(target_dir)
        is_repo = git_adapter.is_git_repo()
        table.add_row("Git CLI", SYM_CHECK, f"Installed ({git_path}), Repo: {'Yes' if is_repo else 'No'}")
    else:
        table.add_row("Git CLI", SYM_CROSS, "Git is not installed or not in PATH")

    # 3. Docker Check
    docker_ok = DockerSandbox.is_docker_available()
    if docker_ok:
        table.add_row("Docker Sandbox", SYM_CHECK, "Docker daemon running & responsive")
    else:
        table.add_row("Docker Sandbox", SYM_WARN, "Docker not available (Local sandbox used as default)")

    # 4. Workspace Permissions
    try:
        test_file = target_dir / ".doctor_perm_test.tmp"
        test_file.write_text("ok", encoding="utf-8")
        test_file.unlink()
        table.add_row("Workspace Permissions", SYM_CHECK, f"Read/Write OK on {target_dir}")
    except Exception as e:
        table.add_row("Workspace Permissions", SYM_CROSS, f"Permission error: {e}")

    # 5. Configured Model & Provider
    provider = create_provider(config.provider)
    prov_ok, prov_msg = provider.check_health()
    status_sym = SYM_CHECK if prov_ok else (SYM_WARN if config.provider.name == "mock" else SYM_CROSS)
    prov_name = config.provider.name.value if hasattr(config.provider.name, "value") else str(config.provider.name)
    table.add_row(f"Provider ({prov_name})", status_sym, f"Model: {config.provider.model} - {prov_msg}")

    console.print(table)
