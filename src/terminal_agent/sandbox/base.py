"""Base interface for sandbox environments."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional


@dataclass
class ExecutionResult:
    command: str
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int
    timed_out: bool = False

    @property
    def is_success(self) -> bool:
        return self.exit_code == 0 and not self.timed_out


class Sandbox(ABC):
    """Abstract sandbox runner."""

    @abstractmethod
    def execute(
        self,
        command: str,
        cwd: Optional[Path] = None,
        timeout: Optional[int] = None,
        env: Optional[Dict[str, str]] = None
    ) -> ExecutionResult:
        """Execute a command in the sandbox environment."""
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Perform any cleanup needed by the sandbox."""
        pass

