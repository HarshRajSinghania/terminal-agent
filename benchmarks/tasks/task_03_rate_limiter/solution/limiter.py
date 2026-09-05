import time
from collections import defaultdict
from typing import Dict, List

class SlidingWindowRateLimiter:
    def __init__(self, max_requests: int, window_seconds: float):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.user_requests: Dict[str, List[float]] = defaultdict(list)

    def is_allowed(self, user_id: str, current_time: float = None) -> bool:
        now = current_time if current_time is not None else time.time()
        cutoff = now - self.window_seconds
        # Evict timestamps older than cutoff window
        valid_timestamps = [t for t in self.user_requests[user_id] if t > cutoff]
        self.user_requests[user_id] = valid_timestamps

        if len(valid_timestamps) < self.max_requests:
            self.user_requests[user_id].append(now)
            return True
        return False

