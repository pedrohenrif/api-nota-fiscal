from __future__ import annotations

from typing import Any

from services.extractor.oracle_dsn import parse_oracle_dsn
from services.extractor.oracle_init import ensure_oracle_client


class OracleSession:
    """Conexao Oracle persistente (commit/rollback controlados pelo caller)."""

    def __init__(self, dsn: str, nome: str = "oracle"):
        self._dsn = dsn
        self.nome = nome
        self._conn = None
        self._config = parse_oracle_dsn(dsn)

    def connect(self) -> None:
        import oracledb

        ensure_oracle_client()
        if self._config["mode"] == "connect_string":
            self._conn = oracledb.connect(dsn=self._config["connect_string"])
        else:
            self._conn = oracledb.connect(
                user=self._config["user"],
                password=self._config["password"],
                host=self._config["host"],
                port=self._config["port"],
                service_name=self._config["service_name"],
            )

    def close(self) -> None:
        if self._conn is not None:
            try:
                self._conn.close()
            finally:
                self._conn = None

    def commit(self) -> None:
        if self._conn is None:
            raise RuntimeError(f"[{self.nome}] conexao nao estabelecida")
        self._conn.commit()

    def rollback(self) -> None:
        if self._conn is None:
            return
        self._conn.rollback()

    def fetch_all(self, sql: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        if self._conn is None:
            raise RuntimeError(f"[{self.nome}] conexao nao estabelecida")
        with self._conn.cursor() as cursor:
            cursor.execute(sql, params or {})
            if cursor.description is None:
                return []
            columns = [c[0] for c in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def fetch_value(self, sql: str, params: dict[str, Any] | None = None) -> Any:
        rows = self.fetch_all(sql, params)
        if not rows:
            return None
        return next(iter(rows[0].values()))

    def execute(self, sql: str, params: dict[str, Any] | None = None) -> int:
        if self._conn is None:
            raise RuntimeError(f"[{self.nome}] conexao nao estabelecida")
        with self._conn.cursor() as cursor:
            cursor.execute(sql, params or {})
            return int(cursor.rowcount or 0)

    def callproc_with_outs(self, name: str, args: list[Any]) -> list[Any]:
        """callproc preservando OUT binds (vars do cursor)."""
        if self._conn is None:
            raise RuntimeError(f"[{self.nome}] conexao nao estabelecida")
        with self._conn.cursor() as cursor:
            cursor.callproc(name, args)
            return args

    @property
    def connection(self):
        return self._conn
