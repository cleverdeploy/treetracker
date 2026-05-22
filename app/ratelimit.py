"""Simple per-user in-process rate limiter."""

from __future__ import annotations

import time
import uuid
from collections import defaultdict, deque
from threading import Lock

WINDOW_SEC = 3600
MAX_REQ = 30

_buckets: dict[uuid.UUID, deque[float]] = defaultdict(deque)
_lock = Lock()


def check(user_id: uuid.UUID) -> bool:
    """Return True if request is allowed; False if rate-limited."""
    now = time.time()
    with _lock:
        bucket = _buckets[user_id]
        while bucket and bucket[0] < now - WINDOW_SEC:
            bucket.popleft()
        if len(bucket) >= MAX_REQ:
            return False
        bucket.append(now)
        return True
