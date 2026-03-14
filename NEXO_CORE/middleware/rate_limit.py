import time
from collections import defaultdict
from fastapi import HTTPException

class InMemoryRateLimiter:
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window = window_seconds
        self._buckets: dict[str, list[float]] = defaultdict(list)
    def check(self, key: str) -> None:
        now = time.monotonic()
        bucket = self._buckets[key]
        self._buckets[key] = [t for t in bucket if now - t < self.window]
        if len(self._buckets[key]) >= self.max_requests:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        self._buckets[key].append(now)
