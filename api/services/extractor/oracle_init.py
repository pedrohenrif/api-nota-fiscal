from __future__ import annotations

import os
from threading import Lock

_lock = Lock()
_initialized = False


def _discover_instant_client() -> str | None:
    base = "/opt/oracle"
    if not os.path.isdir(base):
        return None

    candidates = sorted(
        (
            os.path.join(base, name)
            for name in os.listdir(base)
            if name.startswith("instantclient_") and os.path.isdir(os.path.join(base, name))
        ),
        reverse=True,
    )
    return candidates[0] if candidates else None


def ensure_oracle_client() -> None:
    global _initialized
    if _initialized:
        return

    with _lock:
        if _initialized:
            return

        import oracledb

        lib_dir = os.getenv("ORACLE_CLIENT_LIB_DIR", "").strip() or _discover_instant_client() or ""

        if not lib_dir or not os.path.isdir(lib_dir):
            raise RuntimeError(
                "Oracle Instant Client nao encontrado no container. "
                "Monte o diretorio da VM em /opt/oracle/... no docker-compose "
                "e defina ORACLE_CLIENT_LIB_DIR."
            )

        oracledb.init_oracle_client(lib_dir=lib_dir)
        _initialized = True
