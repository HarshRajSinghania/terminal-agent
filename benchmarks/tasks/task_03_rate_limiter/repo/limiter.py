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
        # BUG: forgets to filter out timestamps older than now - self.window_seconds
        timestamps = self.user_requests[user_id]
        if len(timestamps) < self.max_requests:
            timestamps.append(now)
            return True
        return False

