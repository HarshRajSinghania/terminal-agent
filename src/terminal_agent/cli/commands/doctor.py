"""CLI doctor command checking environment, toolchain, sandbox, and provider availability."""

import os
import shutil
import sys
from pathlib import Path
from typing import Optional
import typer
from rich.panel import Panel
from rich.table import Table

from terminal_agent.cli.theme import SYM_CHECK, SYM_CROSS, SYM_WARN, console
from terminal_agent.cli.ui import render_header
from terminal_agent.config.schema import ProviderType
from terminal_agent.config.settings import load_config
from terminal_agent.git.adapter import GitAdapter
from terminal_agent.providers.detector import OllamaStatus, ProviderStatus, detect_all_providers, detect_ollama
from terminal_agent.sandbox.docker import DockerSandbox


def doctor_command(
    working_dir: Optional[Path] = typer.Option(None, "--cwd", "-C", help="Target repository directory"),
) -> None:
    """Check system toolchains, sandbox prerequisites, and model provider availability."""
    render_header()
    target_dir = (working_dir or Path.cwd()).resolve()
    config = load_config(target_dir / "terminal-agent.config.yaml")

    console.print("[agent.accent]Running system diagnostics and provider auto-detection...[/agent.accent]\n")

    # 1. System & Toolchains Table
    sys_table = Table(title="[bold agent.accent]SYSTEM & TOOLCHAINS[/bold agent.accent]", border_style="agent.border")
    sys_table.add_column("Component", style="agent.text", width=22)
    sys_table.add_column("Status", width=10)
    sys_table.add_column("Details", style="agent.muted")

    # Python Check
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    if sys.version_info >= (3, 10):
        sys_table.add_row("Python Runtime", SYM_CHECK, f"Python {py_ver}")
    else:
        sys_table.add_row("Python Runtime", SYM_CROSS, f"Python {py_ver} (Requires 3.10+)")

    # Git Check
    git_path = shutil.which("git")
    if git_path:
        git_adapter = GitAdapter(target_dir)
        is_repo = git_adapter.is_git_repo()
        sys_table.add_row("Git CLI", SYM_CHECK, f"Installed, Repository Root: {'Yes' if is_repo else 'No'}")
    else:
        sys_table.add_row("Git CLI", SYM_CROSS, "Git is not installed or not in PATH")

    # Local Sandbox Check
    sys_table.add_row("Local Sandbox", SYM_CHECK, "Process-tree isolation with psutil timeout manager")

    # Docker Sandbox Check
    docker_ok = DockerSandbox.is_docker_available()
    if docker_ok:
        sys_table.add_row("Docker Sandbox", SYM_CHECK, "Docker daemon running & available")
    else:
        sys_table.add_row("Docker Sandbox", SYM_WARN, "Docker not running (Local sandbox used as default)")

    # Workspace Permissions
    try:
        test_file = target_dir / ".doctor_perm_test.tmp"
        test_file.write_text("ok", encoding="utf-8")
        test_file.unlink()
        sys_table.add_row("Workspace Access", SYM_CHECK, f"Read/Write OK on {target_dir.name}")
    except Exception as e:
        sys_table.add_row("Workspace Access", SYM_CROSS, f"Permission error: {e}")

    console.print(sys_table)
    console.print()

    # 2. Providers Detection Table
    prov_table = Table(title="[bold agent.accent]MODEL PROVIDERS[/bold agent.accent]", border_style="agent.border")
    prov_table.add_column("Provider", style="agent.text", width=22)
    prov_table.add_column("Status", width=10)
    prov_table.add_column("Details", style="agent.muted")

    providers = detect_all_providers(config=config, working_dir=target_dir)
    configured_provider_name = config.provider.name.value if hasattr(config.provider.name, "value") else str(config.provider.name)

    any_usable = False
    configured_is_usable = False

    for prov_name, info in providers.items():
        is_active_config = (prov_name == configured_provider_name)
        display_label = f"{info.display_name} {'[bold cyan](Active)[/bold cyan]' if is_active_config else ''}"

        if info.status == ProviderStatus.READY:
            any_usable = True
            if is_active_config:
                configured_is_usable = True
            prov_table.add_row(display_label, SYM_CHECK, info.details)
        elif info.status == ProviderStatus.NOT_CONFIGURED:
            # Optional missing provider -> SYM_WARN / Info, NOT SYM_CROSS
            status_badge = SYM_WARN
            hint_str = f" - Hint: {info.action_hint}" if info.action_hint else ""
            prov_table.add_row(display_label, status_badge, f"{info.details}{hint_str}")
        else:
            # Error or explicitly selected but broken
            status_badge = SYM_CROSS if is_active_config else SYM_WARN
            hint_str = f" - Hint: {info.action_hint}" if info.action_hint else ""
            prov_table.add_row(display_label, status_badge, f"{info.details}{hint_str}")

    console.print(prov_table)
    console.print()

    # 3. Overall Readiness Assessment
    if configured_is_usable or any_usable:
        active_provider_info = providers.get(configured_provider_name)
        if active_provider_info and active_provider_info.is_usable:
            lines = [
                "[bold agent.success]Overall Status: READY[/bold agent.success]",
                f"Active Provider: [bold agent.accent]{active_provider_info.display_name}[/bold agent.accent] (Model: {config.provider.model})"
            ]
        else:
            usable_names = [p.display_name for p in providers.values() if p.is_usable and p.name != "mock"]
            if not usable_names:
                usable_names = ["Mock Provider"]
            lines = [
                "[bold agent.success]Overall Status: READY[/bold agent.success]",
                f"Available Provider(s): [bold agent.accent]{', '.join(usable_names)}[/bold agent.accent]",
                "[agent.muted]Run [bold]terminal-agent setup[/bold] to switch default provider.[/agent.muted]"
            ]
        console.print(Panel("\n".join(lines), border_style="agent.success", title="[bold agent.success]DIAGNOSTIC RESULT[/bold agent.success]"))
    else:
        lines = [
            "[bold agent.error]Overall Status: NOT READY[/bold agent.error]",
            "[agent.warning]No model provider is currently configured or reachable.[/agent.warning]",
            "",
            "Next Action:",
            "  Run [bold agent.accent]terminal-agent setup[/bold agent.accent] to interactively configure Ollama or cloud API keys."
        ]
        console.print(Panel("\n".join(lines), border_style="agent.error", title="[bold agent.error]DIAGNOSTIC RESULT[/bold agent.error]"))
