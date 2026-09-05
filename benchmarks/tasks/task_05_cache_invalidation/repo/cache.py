from typing import Any, Dict, Optional

class InMemoryCache:
    def __init__(self):
        self._store: Dict[str, Any] = {}

    def get(self, key: str) -> Optional[Any]:
        return self._store.get(key)

    def set(self, key: str, value: Any) -> None:
        self._store[key] = value

    def invalidate(self, key: str) -> bool:
        # BUG: no-op stub
        return False

    def clear_prefix(self, prefix: str) -> int:
        # BUG: returns 0 without deleting keys
        return 0
