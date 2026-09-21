"""Bounded exponential backoff with an injectable sleep (tests never really sleep)."""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class RetryPolicy:
    attempts: int = 3          # total tries, including the first one
    base_delay: float = 0.5    # seconds before the 2nd try
    factor: float = 2.0
    max_delay: float = 8.0

    def delays(self) -> list[float]:
        """Sleep durations between tries: attempts=3 -> [0.5, 1.0]."""
        return [min(self.max_delay, self.base_delay * (self.factor ** i)) for i in range(max(0, self.attempts - 1))]


class RetryError(Exception):
    """All attempts failed. `last` is the final exception, `attempts` how many were made."""

    def __init__(self, attempts: int, last: BaseException) -> None:
        super().__init__(f"failed after {attempts} attempt(s): {type(last).__name__}: {last}")
        self.attempts = attempts
        self.last = last


def retry_call(
    func: Callable[[], T],
    policy: RetryPolicy = RetryPolicy(),
    sleep: Callable[[float], None] = time.sleep,
    retry_on: tuple[type[BaseException], ...] = (Exception,),
) -> tuple[T, int]:
    """Call `func` until it succeeds; return (result, attempts_made) or raise RetryError."""
    delays = policy.delays()
    total = max(1, policy.attempts)
    for attempt in range(1, total + 1):
        try:
            return func(), attempt
        except retry_on as exc:  # noqa: PERF203 - the loop is the point
            if attempt >= total:
                raise RetryError(attempt, exc) from exc
            sleep(delays[attempt - 1])
    raise AssertionError("unreachable")  # pragma: no cover
