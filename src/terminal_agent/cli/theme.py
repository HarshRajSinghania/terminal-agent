"""Rich theme and color definitions adhering to Terminal Agent monochrome aesthetic."""

import os
import sys
from rich.console import Console
from rich.theme import Theme

# Force UTF-8 on Windows terminal if available
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Terminal Agent Monochrome Palette
PALETTE = {
    "bg": "#0A0A0A",
    "text": "#EDEDED",
    "muted": "#8A8A8A",
    "success": "#69F0AE",
    "warning": "#FFC857",
    "error": "#FF5F56",
    "accent": "#F5F5F5",
    "cyan_accent": "#00E5FF",
    "orange_accent": "#FF9100",
}

TERMINAL_AGENT_THEME = Theme({
    "agent.title": f"bold {PALETTE['accent']}",
    "agent.tagline": f"italic {PALETTE['muted']}",
    "agent.text": PALETTE["text"],
    "agent.muted": PALETTE["muted"],
    "agent.success": f"bold {PALETTE['success']}",
    "agent.warning": f"bold {PALETTE['warning']}",
    "agent.error": f"bold {PALETTE['error']}",
    "agent.accent": f"bold {PALETTE['accent']}",
    "agent.cyan": PALETTE["cyan_accent"],
    "agent.orange": PALETTE["orange_accent"],
    "agent.code": f"{PALETTE['accent']} on #1E1E1E",
    "agent.border": "#333333",
})

console = Console(theme=TERMINAL_AGENT_THEME, legacy_windows=False)
error_console = Console(theme=TERMINAL_AGENT_THEME, stderr=True, legacy_windows=False)

# Symbols (Safe UTF-8 with fallback)
SYM_CHECK = "[agent.success]✓[/agent.success]"
SYM_CROSS = "[agent.error]✗[/agent.error]"
SYM_ARROW = "[agent.accent]→[/agent.accent]"
SYM_BULLET = "[agent.muted]•[/agent.muted]"
SYM_WARN = "[agent.warning]![/agent.warning]"

