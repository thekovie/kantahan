"""A sliding-window limiter. State lives in memory: one worker process, reset on restart.

Memory is bounded: visitors whose newest request has left the window are forgotten (oldest first),
and the number of tracked visitors has a hard ceiling, oldest dropped first.
"""

from __future__ import annotations

from collections import OrderedDict, deque
from collections.abc import Callable

MAX_KEYS = 10_000


class SlidingWindow:
    def __init__(self, limit: int, window: float, clock: Callable[[], float]) -> None:
        self._limit, self._window, self._clock = limit, window, clock
        self._seen: OrderedDict[str, deque[float]] = OrderedDict()  # least recently active first

    def tracked(self) -> int:
        return len(self._seen)

    def _forget_idle(self, now: float) -> None:
        while self._seen:
            oldest = next(iter(self._seen))
            events = self._seen[oldest]
            if events and now - events[-1] < self._window:
                break
            del self._seen[oldest]

    def check(self, key: str) -> int:
        """0 when `key` may go ahead, otherwise the seconds until it may. Never stores anything."""
        now = self._clock()
        events = self._seen.get(key)
        if not events:
            return 0
        while events and now - events[0] >= self._window:
            events.popleft()
        if len(events) < self._limit:
            return 0
        return max(int(self._window - (now - events[0])) + 1, 1)

    def record(self, key: str) -> None:
        now = self._clock()
        events = self._seen.setdefault(key, deque())
        while events and now - events[0] >= self._window:
            events.popleft()
        events.append(now)
        self._seen.move_to_end(key)
        self._forget_idle(now)
        while len(self._seen) > MAX_KEYS:
            self._seen.popitem(last=False)
