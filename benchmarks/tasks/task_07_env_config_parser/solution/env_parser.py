import os
from typing import Any, Type

def parse_env_var(key: str, var_type: Type = str, default: Any = None) -> Any:
    """Parse typed environment variable."""
    val = os.getenv(key)
    if val is None:
        return default

    if var_type is bool:
        return val.strip().lower() in ("true", "1", "yes", "on", "t")
    try:
        return var_type(val)
    except Exception:
        return default

