from __future__ import annotations

import time
from typing import Callable, TypeVar

from openai import OpenAI

T = TypeVar("T")

client = OpenAI()

MAX_ATTEMPTS = 3
BASE_SLEEP_SEC = 0.7


def call_with_retry(fn: Callable[[], T]) -> T:
    """
    Minimal retry wrapper for OpenAI calls.
    Retries transient failures (rate limit, timeout, 5xx).
    """
    last_err: Exception | None = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            return fn()
        except Exception as e:
            last_err = e
            msg = str(e).lower()

            retryable = any(k in msg for k in [
                "429", "rate", "timeout",
                "temporar", "503", "502",
                "connection", "network"
            ])

            if attempt == MAX_ATTEMPTS or not retryable:
                raise

            sleep_for = BASE_SLEEP_SEC * (2 ** (attempt - 1))
            time.sleep(sleep_for)

    raise last_err if last_err else RuntimeError("OpenAI call failed")