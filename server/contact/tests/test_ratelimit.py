from kantahan_contact import ratelimit
from kantahan_contact.ratelimit import SlidingWindow


class Clock:
    now = 0.0

    def __call__(self):
        return self.now


def test_expired_visitors_are_forgotten_without_ever_returning():
    clock = Clock()
    limiter = SlidingWindow(5, 3600, clock)
    for i in range(1000):
        limiter.record(f"visitor-{i}")
    clock.now += 4000
    limiter.record("someone-new")
    assert limiter.tracked() == 1


def test_the_number_of_tracked_visitors_has_a_hard_ceiling(monkeypatch):
    monkeypatch.setattr(ratelimit, "MAX_KEYS", 50)
    clock = Clock()
    limiter = SlidingWindow(5, 3600, clock)
    for i in range(500):
        clock.now += 0.001
        limiter.record(f"visitor-{i}")
    assert limiter.tracked() <= 50


def test_the_limit_and_the_wait_time_still_work():
    clock = Clock()
    limiter = SlidingWindow(2, 100, clock)
    for _ in range(2):
        assert limiter.check("a") == 0
        limiter.record("a")
    assert 0 < limiter.check("a") <= 101
    clock.now += 101
    assert limiter.check("a") == 0
