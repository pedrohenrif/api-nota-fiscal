from __future__ import annotations

import os
from threading import Lock

_lock = Lock()
_initialized = False


def ensure_oracle_client() -> None:
    global _initialized
    if _initialized:
        return

    with _lock:
        if _initialized:
            return

        import oracledb

        lib_dir = os.getenv("ORACLE_CLIENT_LIB_DIR", "").strip()
        if not lib_dir:
            for candidate in (
                "/opt/oracle/instantclient_21_15",
                "/opt/oracle/instantclient_19_23",
            ):
                if os.path.isdir(candidate):
                    lib_dir = candidate
                    break

        if not lib_dir:
            raise RuntimeError(
                "Oracle Instant Client nao encontrado. Reconstrua a imagem Docker "
                "(docker compose build extractor-service) ou defina ORACLE_CLIENT_LIB_DIR."
            )

        oracledb.init_oracle_client(lib_dir=lib_dir)
        _initialized = True
