"""Rich UI rendering components for the monochrome Terminal Agent aesthetic."""

from pathlib import Path
from typing import Any, Dict, List, Optional
from rich.box import ROUNDED, HEAVY, DOUBLE
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from terminal_agent.cli.theme import (
    PALETTE,
    SYM_ARROW,
    SYM_CHECK,
    SYM_CROSS,
    SYM_WARN,
    console,
)
from terminal_agent.session.models import PlanItem, TaskContract, VerificationResult, VerificationStatus


def render_header() -> None:
    """Render main application banner."""
    content = Text()
    content.append("TERMINAL AGENT\n", style="agent.title")
    content.append("Build. Verify. Ship.", style="agent.tagline")
    panel = Panel(content, box=ROUNDED, border_style="agent.border", padding=(0, 2))
    console.print(panel)


def render_task_card(task: str, project_dir: Path) -> None:
    """Render current project and task context."""
    t = Table.grid(padding=(0, 2))
    t.add_column(style="agent.muted", width=12)
    t.add_column(style="agent.text")

    t.add_row("PROJECT", str(project_dir))
    t.add_row("TASK", task)
    console.print(Panel(t, box=ROUNDED, border_style="agent.border"))


def render_contract_card(contract: TaskContract) -> None:
    """Render negotiated Task Contract."""
    t = Table(box=ROUNDED, border_style="agent.border", show_header=False, expand=True)
    t.add_column("Key", style="agent.muted", width=16)
    t.add_column("Value", style="agent.text")

    t.add_row("GOAL", contract.goal)
    t.add_row("CONSTRAINTS", "\n".join(f"• {c}" for c in contract.constraints))
    t.add_row("SUCCESS CRITERIA", "\n".join(f"• {sc}" for sc in contract.success_criteria))
    t.add_row("VERIFY COMMANDS", ", ".join(contract.verification_commands))

    console.print(Panel(t, title="[agent.accent]TASK CONTRACT[/agent.accent]", border_style="agent.border"))


def render_plan(plan: List[PlanItem]) -> None:
    """Render live plan status."""
    lines = []
    for item in plan:
        if item.status == "COMPLETED":
            symbol = SYM_CHECK
            style = "agent.text"
        elif item.status == "IN_PROGRESS":
            symbol = SYM_ARROW
            style = "agent.accent"
        elif item.status == "FAILED":
            symbol = SYM_CROSS
            style = "agent.error"
        else:
            symbol = "[agent.muted]○[/agent.muted]"
            style = "agent.muted"
        lines.append(f"{symbol} [{style}]{item.description}[/{style}]")

    console.print(Panel("\n".join(lines), title="[agent.accent]PLAN[/agent.accent]", border_style="agent.border"))


def render_tool_event(tool_name: str, reason: str, status: str = "success", duration_ms: Optional[int] = None) -> None:
    """Render a step in the action timeline with explainability reason."""
    dur_str = f" [agent.muted]({duration_ms}ms)[/agent.muted]" if duration_ms is not None else ""
    symbol = SYM_CHECK if status == "success" else (SYM_CROSS if status == "error" else SYM_ARROW)
    
    t = Table.grid(padding=(0, 1))
    t.add_column(width=4)
    t.add_column()
    t.add_row(symbol, f"[agent.accent]{tool_name}[/agent.accent]{dur_str}")
    if reason:
        t.add_row("", f"[agent.muted]Reason: {reason}[/agent.muted]")
    console.print(t)


def render_verification_result(result: VerificationResult) -> None:
    """Render independent verification card."""
    is_verified = result.status == VerificationStatus.VERIFIED
    border_col = "agent.success" if is_verified else ("agent.warning" if result.status == VerificationStatus.PARTIAL else "agent.error")
    title_text = f"[{border_col}]VERIFICATION: {result.status.value}[/{border_col}]"

    table = Table(box=ROUNDED, border_style=border_col, show_header=False, expand=True)
    table.add_column("Key", style="agent.muted", width=16)
    table.add_column("Value", style="agent.text")

    table.add_row("TESTS", f"{result.tests_passed}/{result.tests_run} passed ({result.tests_failed} failed)")
    table.add_row("LINT", "[agent.success]PASS[/agent.success]" if result.lint_passed else "[agent.error]FAIL[/agent.error]")
    table.add_row("FILES CHANGED", f"{result.files_changed_count} files ({', '.join(result.files_changed) if result.files_changed else 'None'})")

    if result.assertions:
        assertions_str = "\n".join(
            f"{SYM_CHECK if a.passed else SYM_CROSS} {a.name}: {a.message}"
            for a in result.assertions
        )
        table.add_row("ASSERTIONS", assertions_str)

    console.print(Panel(table, title=title_text, border_style=border_col))


def render_proof_of_done(pod: Dict[str, Any], duration_seconds: float = 0.0) -> None:
    """Render final certified Proof of Done."""
    mins = int(duration_seconds // 60)
    secs = int(duration_seconds % 60)
    time_str = f"{mins:02d}m {secs:02d}s"

    t = Table(box=ROUNDED, border_style="agent.success", show_header=False, expand=True)
    t.add_column("Key", style="agent.muted", width=18)
    t.add_column("Value", style="agent.text")

    t.add_row("TASK", pod.get("task", ""))
    t.add_row("RESULT", f"[agent.success]{pod.get('result', 'VERIFIED')}[/agent.success]")
    t.add_row("TESTS", f"[agent.success]{pod.get('tests_passed', 'N/A')}[/agent.success]")
    t.add_row("LINT", pod.get("lint", "PASS"))
    t.add_row("FILES CHANGED", f"{pod.get('files_changed_count', 0)} ({', '.join(pod.get('files_changed', []))})")
    t.add_row("UNINTENDED FILES", str(pod.get("unintended_files_count", 0)))
    t.add_row("RETRIES", str(pod.get("retries_count", 0)))
    t.add_row("SUCCESS CRITERIA", pod.get("success_criteria_passed", "N/A"))
    t.add_row("EXECUTION TIME", time_str)

    console.print()
    console.print(Panel(t, title="[agent.success]PROOF OF DONE[/agent.success]", border_style="agent.success"))

    summary = pod.get("summary", {})
    if summary:
        sum_table = Table(box=ROUNDED, border_style="agent.border", show_header=False, expand=True)
        sum_table.add_column("Key", style="agent.muted", width=18)
        sum_table.add_column("Value", style="agent.text")
        sum_table.add_row("WHAT CHANGED", summary.get("what_changed", ""))
        sum_table.add_row("WHY IT CHANGED", summary.get("why_it_changed", ""))
        sum_table.add_row("WHAT WAS VERIFIED", summary.get("what_was_verified", ""))
        sum_table.add_row("LIMITATIONS", summary.get("remaining_limitations", "None"))
        console.print(Panel(sum_table, title="[agent.accent]FINAL SUMMARY[/agent.accent]", border_style="agent.border"))
