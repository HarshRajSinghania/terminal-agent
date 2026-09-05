"""Command safety classifier and policy inspector."""

import re
import shlex
from typing import List, Tuple
from terminal_agent.config.schema import CommandCategory


SAFE_COMMANDS = {
    "pytest", "pytest-3", "python -m pytest", "python3 -m pytest",
    "git status", "git diff", "git log", "git show", "git branch", "git rev-parse",
    "ls", "dir", "echo", "pwd", "whoami", "cat", "type", "head", "tail", "wc",
    "npm test", "npm run test", "yarn test", "cargo test", "go test",
    "flake8", "black --check", "mypy", "ruff check", "pylint",
    "find", "grep", "rg",
}

SAFE_BINARIES = {
    "pytest", "pytest-3", "git", "ls", "echo", "pwd", "whoami", "cat",
    "head", "tail", "wc", "flake8", "mypy", "ruff", "pylint", "grep", "rg"
}

DESTRUCTIVE_PATTERNS = [
    r"\brm\s+(-[rfRF]+\s+|--recursive\s+|--force\s+)",
    r"\bdel\s+/[sfqSFQ]",
    r"\brmdir\s+/[sqSQ]",
    r"\bformat\b",
    r"\bdd\s+if=",
    r"\bmkfs\b",
    r">\s*/dev/sd[a-z]",
    r"\bdrop\s+database\b",
    r"\bdrop\s+table\b",
    r"\btruncate\s+table\b",
    r"\bchmod\s+-R\s+777\b",
    r"\bchown\s+-R\b",
    r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;",  # fork bomb
]

NETWORK_PATTERNS = [
    r"\bcurl\b",
    r"\bwget\b",
    r"\bssh\b",
    r"\bscp\b",
    r"\bsftp\b",
    r"\brsync\b",
    r"\bftp\b",
    r"\btelnet\b",
    r"\bnc\b",
    r"\bnetcat\b",
    r"\bnmap\b",
    r"\bping\b",
    r"\btraceroute\b",
    r"\bgit\s+clone\b",
    r"\bgit\s+push\b",
    r"\bgit\s+pull\b",
    r"\bgit\s+fetch\b",
    r"\bpip\s+install\s+http",
    r"\bnpm\s+publish\b",
]

PRIVILEGED_PATTERNS = [
    r"\bsudo\b",
    r"\bsu\s+",
    r"\bdoas\b",
    r"\brun-as\b",
    r"\bpowershell\s+-ExecutionPolicy\s+Bypass\b",
    r"\bnet\s+user\b",
    r"\bnet\s+localgroup\b",
    r"\breg\s+add\b",
    r"\breg\s+delete\b",
    r"\bpasswd\b",
    r"\buseradd\b",
    r"\buserdel\b",
    r"\bvisudo\b",
    r"\biptables\b",
    r"\bufw\b",
    r"\bsystemctl\b",
    r"\bservice\b",
]

WRITE_PATTERNS = [
    r"\bmkdir\b",
    r"\btouch\b",
    r"\bcp\b",
    r"\bmv\b",
    r"\bcopy\b",
    r"\bmove\b",
    r"\bren\b",
    r"\bdel\b",
    r"\brm\b",
    r"\brmdir\b",
    r"\bgit\s+add\b",
    r"\bgit\s+commit\b",
    r"\bgit\s+checkout\b",
    r"\bgit\s+restore\b",
    r"\bgit\s+reset\b",
    r"\bgit\s+stash\b",
    r"\bgit\s+clean\b",
]


class CommandClassifier:
    """Classifies terminal commands to determine safety risks and approval requirements."""

    @classmethod
    def classify(cls, command: str) -> Tuple[CommandCategory, str]:
        """
        Classify a command string.
        Returns (CommandCategory, reason).
        """
        cmd_clean = command.strip()
        if not cmd_clean:
            return CommandCategory.SAFE, "Empty command"

        # Check privileged first (highest risk)
        for pattern in PRIVILEGED_PATTERNS:
            if re.search(pattern, cmd_clean, re.IGNORECASE):
                return CommandCategory.PRIVILEGED, f"Matched privileged pattern: {pattern}"

        # Check destructive
        for pattern in DESTRUCTIVE_PATTERNS:
            if re.search(pattern, cmd_clean, re.IGNORECASE):
                return CommandCategory.DESTRUCTIVE, f"Matched destructive pattern: {pattern}"

        # Check network
        for pattern in NETWORK_PATTERNS:
            if re.search(pattern, cmd_clean, re.IGNORECASE):
                return CommandCategory.NETWORK, f"Matched network pattern: {pattern}"

        # Check if exactly matching safe command list
        lowered = cmd_clean.lower()
        if any(lowered == safe or lowered.startswith(f"{safe} ") for safe in SAFE_COMMANDS):
            # Special check: git checkout / git reset might write
            if "git checkout" in lowered or "git reset" in lowered or "git clean" in lowered:
                return CommandCategory.WRITE, "Git state modification command"
            return CommandCategory.SAFE, "Matched safe command whitelist"

        # Check write patterns
        for pattern in WRITE_PATTERNS:
            if re.search(pattern, cmd_clean, re.IGNORECASE):
                return CommandCategory.WRITE, f"Matched write pattern: {pattern}"

        # If it's a test runner or python file execution without destructive markers
        if re.search(r"^(python|python3|node|cargo|go)\s+", cmd_clean):
            if "test" in cmd_clean or "-m unittest" in cmd_clean or "-m pytest" in cmd_clean:
                return CommandCategory.SAFE, "Test suite runner"
            return CommandCategory.WRITE, "General code execution"

        # Default fallback
        return CommandCategory.WRITE, "Default standard execution"

