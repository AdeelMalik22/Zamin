from collections import defaultdict, deque
from threading import Lock
import time

from app.exceptions.custom_exceptions import RateLimitError


class LoginRateLimiter:
    """In-process guard for local SQLite deployments.

    Replace this with a shared Redis/requestguard limiter for multi-process
    production deployments.
    """

    def __init__(self, attempts: int = 5, window_seconds: int = 600) -> None:
        self.attempts = attempts
        self.window_seconds = window_seconds
        self._failures: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def _prune(self, attempts: deque[float], now: float) -> None:
        while attempts and now - attempts[0] >= self.window_seconds:
            attempts.popleft()

    def ensure_allowed(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            attempts = self._failures[key]
            self._prune(attempts, now)
            if len(attempts) >= self.attempts:
                raise RateLimitError("too many failed login attempts; try again later")

    def record_failure(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            attempts = self._failures[key]
            self._prune(attempts, now)
            attempts.append(now)

    def reset(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)


login_rate_limiter = LoginRateLimiter()
