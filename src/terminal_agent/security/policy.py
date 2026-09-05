"""Security policy enforcer for Terminal Agent."""

from typing import Callable, Optional
from terminal_agent.config.schema import CommandCategory, SecurityConfig
from terminal_agent.security.classifier import CommandClassifier
from terminal_agent.security.secrets import SecretGuard


class SecurityPolicyEnforcer:
    """Enforces execution boundaries, secret protections, and user confirmation policies."""

    def __init__(
        self,
        security_config: Optional[SecurityConfig] = None,
        secret_guard: Optional[SecretGuard] = None,
        confirmation_callback: Optional[Callable[[str, CommandCategory, str], bool]] = None
    ):
        self.config = security_config or SecurityConfig()
        self.guard = secret_guard or SecretGuard(blocked_patterns=self.config.blocked_paths)
        self.confirmation_callback = confirmation_callback

    def check_command(self, command: str) -> tuple[bool, str, CommandCategory]:
        """
        Evaluate if a command is allowed to execute.
        Returns (is_allowed, reason, category).
        """
        category, reason = CommandClassifier.classify(command)

        # Check network policy
        if category == CommandCategory.NETWORK and self.config.network == "disabled":
            return False, f"Network access is disabled by security policy. (Triggered by: {command})", category

        # Check if category requires confirmation
        if category in self.config.require_confirmation_for:
            if self.confirmation_callback:
                approved = self.confirmation_callback(command, category, reason)
                if not approved:
                    return False, f"Execution of {category.value} command was rejected by user: {command}", category
            else:
                # If no interactive callback, deny privileged and destructive commands
                if category in (CommandCategory.PRIVILEGED, CommandCategory.DESTRUCTIVE):
                    return False, f"Non-interactive session denied dangerous command ({category.value}): {command}", category

        return True, f"Command allowed ({category.value})", category

    def check_file_path(self, file_path: str, operation: str = "read") -> tuple[bool, str]:
        """Check if file operation is permitted."""
        if self.guard.is_path_blocked(file_path):
            return False, f"Access to '{file_path}' is blocked by secret protection policy."
        return True, "Path allowed"

