"""Path and secret protection engine for Terminal Agent."""

import fnmatch
from pathlib import Path
from typing import List, Optional


DEFAULT_BLOCKED_PATTERNS = [
    ".env",
    ".env.*",
    "*.env",
    "*.pem",
    "*.key",
    "*.pfx",
    "*.p12",
    "id_rsa*",
    "id_ed25519*",
    "id_dsa*",
    "id_ecdsa*",
    "*credential*",
    "*secret*",
    ".ssh/*",
    ".aws/*",
    ".gnupg/*",
    ".docker/config.json",
    ".netrc",
]


class SecretGuard:
    """Protects host and repository secrets from being exposed to LLM or overwritten."""

    def __init__(self, blocked_patterns: Optional[List[str]] = None, working_dir: Optional[Path] = None):
        self.blocked_patterns = blocked_patterns or DEFAULT_BLOCKED_PATTERNS
        self.working_dir = (working_dir or Path.cwd()).resolve()

    def is_path_blocked(self, file_path: Path | str) -> bool:
        """Check whether a given path is blocked by security policy."""
        try:
            p = Path(file_path)
            # Normalize path
            if not p.is_absolute():
                p = (self.working_dir / p).resolve()
            else:
                p = p.resolve()

            # Disallow access outside working directory
            try:
                p.relative_to(self.working_dir)
            except ValueError:
                # Path escapes workspace root
                return True

            filename = p.name
            rel_str = str(p.relative_to(self.working_dir)).replace("\\", "/")

            for pattern in self.blocked_patterns:
                # Pattern match against filename
                if fnmatch.fnmatch(filename.lower(), pattern.lower()):
                    return True
                # Pattern match against relative path
                if fnmatch.fnmatch(rel_str.lower(), pattern.lower()):
                    return True
                # Pattern match for wildcard subdirs
                if fnmatch.fnmatch(rel_str.lower(), f"**/{pattern}".lower()):
                    return True

            return False
        except Exception:
            return True

    def sanitize_env(self, env: Optional[dict] = None) -> dict:
        """Sanitize environment variables, removing sensitive host keys."""
        import os
        source = env if env is not None else os.environ.copy()
        sanitized = {}

        sensitive_keywords = [
            "SECRET", "KEY", "TOKEN", "PASSWORD", "PASS", "AUTH",
            "CREDENTIAL", "AWS_ACCESS", "SSH_AUTH", "PRIVATE"
        ]

        for k, v in source.items():
            upper_k = k.upper()
            # Allow model provider keys if needed internally, but strip generic host secrets
            if any(kw in upper_k for kw in sensitive_keywords):
                # Only pass whitelisted provider envs if necessary
                if k in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "OLLAMA_HOST"):
                    sanitized[k] = v
                else:
                    continue
            else:
                sanitized[k] = v

        return sanitized
