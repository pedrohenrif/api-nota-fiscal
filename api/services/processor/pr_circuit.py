from __future__ import annotations

import threading
import time
from typing import Any

from services.processor.config import (
    PR_CIRCUIT_FAILURE_THRESHOLD,
    PR_CIRCUIT_OPEN_SECONDS,
)


def is_pr_timeout_error(message: str | None) -> bool:
    if not message:
        return False
    text = str(message).casefold()
    if "circuit breaker" in text:
        return False
    return any(
        token in text
        for token in (
            "timed out",
            "readtimeout",
            "connecttimeout",
            "connect timeout",
            "timeout exceeded",
            "execution timeout",
            "timeout expired",
            "timeout period elapsed",
        )
    )


class PrCircuitBreaker:
    """Abre apos N timeouts consecutivos; bloqueia chamadas ao PR por um periodo."""

    def __init__(
        self,
        failure_threshold: int = PR_CIRCUIT_FAILURE_THRESHOLD,
        open_seconds: int = PR_CIRCUIT_OPEN_SECONDS,
    ) -> None:
        self.failure_threshold = max(1, failure_threshold)
        self.open_seconds = max(1, open_seconds)
        self._lock = threading.Lock()
        self._consecutive_timeouts = 0
        self._opened_until: float | None = None
        self._total_opens = 0

    def allow_request(self) -> bool:
        with self._lock:
            if self._opened_until is None:
                return True
            if time.monotonic() >= self._opened_until:
                self._opened_until = None
                self._consecutive_timeouts = 0
                return True
            return False

    def record_success(self) -> None:
        with self._lock:
            self._consecutive_timeouts = 0
            self._opened_until = None

    def record_failure(self, *, is_timeout: bool) -> None:
        if not is_timeout:
            return
        with self._lock:
            self._consecutive_timeouts += 1
            if self._consecutive_timeouts >= self.failure_threshold:
                self._opened_until = time.monotonic() + self.open_seconds
                self._total_opens += 1

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            open_remaining = 0
            state = "closed"
            if self._opened_until is not None:
                remaining = self._opened_until - time.monotonic()
                if remaining > 0:
                    state = "open"
                    open_remaining = int(remaining)
                else:
                    state = "half_open"
            return {
                "state": state,
                "consecutive_timeouts": self._consecutive_timeouts,
                "failure_threshold": self.failure_threshold,
                "open_remaining_seconds": open_remaining,
                "total_opens": self._total_opens,
            }


pr_circuit = PrCircuitBreaker()
