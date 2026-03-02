from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Deque, Dict

from fastapi import HTTPException, Request


class InMemoryRateLimiter:
    def __init__(self, max_requests: int = 120, window_seconds: int = 60) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: Dict[str, Deque[float]] = defaultdict(deque)

    def check(self, key: str) -> None:
        now = time.time()
        window_start = now - self.window_seconds
        queue = self._hits[key]
        while queue and queue[0] < window_start:
            queue.popleft()
        if len(queue) >= self.max_requests:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        queue.append(now)


rate_limiter = InMemoryRateLimiter()


async def enforce_rate_limit(request: Request) -> None:
    client = request.client.host if request.client else "unknown"
    rate_limiter.check(client)
