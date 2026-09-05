"""CLI config command viewing and generating configuration templates."""

from pathlib import Path
from typing import Optional
import typer
import yaml
from rich.syntax import Syntax

from terminal_agent.cli.theme import SYM_CHECK, console
from terminal_agent.cli.ui import render_header
from terminal_agent.config.settings import load_config, save_default_config


def config_command(
    init: bool = typer.Option(False, "--init", "-i", help="Generate default terminal-agent.config.yaml file"),
    working_dir: Optional[Path] = typer.Option(None, "--cwd", "-C", help="Target repository directory"),
) -> None:
    """View active configuration or generate a default configuration file."""
    render_header()
    target_dir = (working_dir or Path.cwd()).resolve()
    target_file = target_dir / "terminal-agent.config.yaml"

    if init:
        save_default_config(target_file)
        console.print(f"{SYM_CHECK} [agent.success]Created default configuration at {target_file}[/agent.success]")
        return

    config = load_config(target_file)
    yaml_str = yaml.dump(config.model_dump(mode="json"), sort_keys=False, indent=2)
    syntax = Syntax(yaml_str, "yaml", theme="monokai", line_numbers=True)
    console.print(syntax)
