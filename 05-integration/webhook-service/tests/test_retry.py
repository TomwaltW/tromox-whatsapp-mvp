from __future__ import annotations

import pytest

from app.retry import RetryError, RetryPolicy, retry_call


def test_succeeds_after_transient_failures_with_exponential_backoff():
    sleeps: list[float] = []
    calls = {"n": 0}

    def flaky() -> str:
        calls["n"] += 1
        if calls["n"] < 3:
            raise ConnectionError("try again")
        return "ok"

    result, attempts = retry_call(flaky, RetryPolicy(attempts=4, base_delay=0.5), sleep=sleeps.append)
    assert (result, attempts) == ("ok", 3) and sleeps == [0.5, 1.0]


def test_gives_up_after_the_bounded_number_of_attempts():
    sleeps: list[float] = []
    calls = {"n": 0}

    def always_fails() -> None:
        calls["n"] += 1
        raise TimeoutError("still down")

    with pytest.raises(RetryError) as excinfo:
        retry_call(always_fails, RetryPolicy(attempts=3, base_delay=1.0), sleep=sleeps.append)
    assert calls["n"] == 3 and sleeps == [1.0, 2.0]
    assert excinfo.value.attempts == 3 and isinstance(excinfo.value.last, TimeoutError)


def test_delays_are_capped_and_non_retryable_errors_propagate():
    assert RetryPolicy(attempts=6, base_delay=1.0, max_delay=4.0).delays() == [1.0, 2.0, 4.0, 4.0, 4.0]
    with pytest.raises(KeyError):
        retry_call(lambda: {}["missing"], RetryPolicy(attempts=3, base_delay=0), sleep=lambda _: None,
                   retry_on=(ConnectionError,))
