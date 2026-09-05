"""Structured event logging and tracing for Terminal Agent actions."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


def get_traces_dir(working_dir: Optional[Path] = None) -> Path:
    """Return .terminal_agent/traces directory."""
    base = working_dir or Path.cwd()
    t_dir = base / ".terminal_agent" / "traces"
    t_dir.mkdir(parents=True, exist_ok=True)
    return t_dir


class TelemetryEvent(BaseModel):
    """Structured telemetry record of an agent action."""
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    session_id: str
    step: int
    event_type: str  # "tool_call", "verification", "failure", "plan_change", "checkpoint"
    tool: Optional[str] = None
    reason: str = Field(default="", description="Explainability reason")
    duration_ms: int = 0
    status: str = "success"  # "success", "error", "pending"
    data: Dict[str, Any] = Field(default_factory=dict)


class TelemetryLogger:
    """Appends telemetry events to local session JSONL trace files."""

    def __init__(self, session_id: str, working_dir: Optional[Path] = None):
        self.session_id = session_id
        self.working_dir = working_dir or Path.cwd()
        self.traces_dir = get_traces_dir(self.working_dir)
        self.trace_file = self.traces_dir / f"{self.session_id}.jsonl"

    def log_event(
        self,
        step: int,
        event_type: str,
        reason: str = "",
        tool: Optional[str] = None,
        duration_ms: int = 0,
        status: str = "success",
        data: Optional[Dict[str, Any]] = None
    ) -> TelemetryEvent:
        """Record and persist an event."""
        event = TelemetryEvent(
            session_id=self.session_id,
            step=step,
            event_type=event_type,
            tool=tool,
            reason=reason,
            duration_ms=duration_ms,
            status=status,
            data=data or {}
        )
        line = event.model_dump_json()
        with open(self.trace_file, "a", encoding="utf-8") as f:
            f.write(line + "\n")
        return event

    @classmethod
    def read_trace(cls, session_id: str, working_dir: Optional[Path] = None) -> List[TelemetryEvent]:
        """Read all telemetry events for a given session."""
        traces_dir = get_traces_dir(working_dir)
        target = traces_dir / f"{session_id}.jsonl"
        if not target.exists():
            candidates = list(traces_dir.glob(f"*{session_id}*.jsonl"))
            if candidates:
                target = candidates[0]
            else:
                return []

        events = []
        with open(target, "r", encoding="utf-8") as f:
            for line in f:
                line_str = line.strip()
                if line_str:
                    try:
                        events.append(TelemetryEvent.model_validate_json(line_str))
                    except Exception:
                        continue
        return events
