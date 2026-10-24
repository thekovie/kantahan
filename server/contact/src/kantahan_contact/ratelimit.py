"""A sliding-window limiter. State lives in memory: one worker process, reset on restart."""

from __future__ import annotations

from collections import deque
from collections.abc import Callable

MAX_KEYS = 10_000


class SlidingWindow:
    def __init__(self, limit: int, window: float, clock: Callable[[], float]) -> None:
        self._limit, self._window, self._clock = limit, window, clock
        self._seen: dict[str, deque[float]] = {}

    def _recent(self, key: str, now: float) -> deque[float]:
        events = self._seen.setdefault(key, deque())
        while events and now - events[0] >= self._window:
            events.popleft()
        return events

    def check(self, key: str) -> int:
        """0 when `key` may go ahead, otherwise the seconds until it may."""
        now = self._clock()
        events = self._recent(key, now)
        if len(events) < self._limit:
            return 0
        return max(int(self._window - (now - events[0])) + 1, 1)

    def record(self, key: str) -> None:
        now = self._clock()
        self._recent(key, now).append(now)
        if len(self._seen) > MAX_KEYS:
            for stale in [k for k, v in self._seen.items() if not v][: MAX_KEYS // 2]:
                del self._seen[stale]
