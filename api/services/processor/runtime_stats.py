from __future__ import annotations

import threading
import time
from typing import Any


class RuntimeStats:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.processed_ok = 0
        self.processed_fail = 0
        self.last_success_at: float | None = None
        self.last_failure_at: float | None = None
        self.last_heartbeat_at: float | None = None
        self.last_error: str | None = None
        self.last_nf: str | None = None
        self.last_result: str | None = None

    def record_success(self, *, nf: str, result: str) -> None:
        with self._lock:
            self.processed_ok += 1
            self.last_success_at = time.time()
            self.last_nf = nf
            self.last_result = result
            self.last_error = None

    def record_failure(self, *, nf: str, result: str, error: str) -> None:
        with self._lock:
            self.processed_fail += 1
            self.last_failure_at = time.time()
            self.last_nf = nf
            self.last_result = result
            self.last_error = error[:500]

    def record_heartbeat(self) -> None:
        """Marca que o consumer esta vivo (mesmo com fila vazia)."""
        with self._lock:
            self.last_heartbeat_at = time.time()

    def snapshot(self, *, queue_depth: int | None = None) -> dict[str, Any]:
        with self._lock:
            now = time.time()
            idle_since_success = None
            if self.last_success_at is not None:
                idle_since_success = int(now - self.last_success_at)
            idle_since_any = None
            last_any = max(
                (
                    t
                    for t in (
                        self.last_success_at,
                        self.last_failure_at,
                        self.last_heartbeat_at,
                    )
                    if t
                ),
                default=None,
            )
            if last_any is not None:
                idle_since_any = int(now - last_any)

            # Stall so faz sentido com mensagens na fila e sem atividade.
            # Fila vazia + consumer rodando = idle normal (nao e travamento).
            backlog = int(queue_depth or 0)
            stalled = bool(
                backlog > 0
                and idle_since_any is not None
                and idle_since_any >= 180
            )
            return {
                "processed_ok": self.processed_ok,
                "processed_fail": self.processed_fail,
                "last_success_at": self.last_success_at,
                "last_failure_at": self.last_failure_at,
                "last_heartbeat_at": self.last_heartbeat_at,
                "last_nf": self.last_nf,
                "last_result": self.last_result,
                "last_error": self.last_error,
                "idle_seconds_since_success": idle_since_success,
                "idle_seconds_since_activity": idle_since_any,
                "queue_depth": backlog,
                "processor_stalled": stalled,
            }


runtime_stats = RuntimeStats()
