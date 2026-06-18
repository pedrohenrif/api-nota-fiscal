from __future__ import annotations

from typing import Any

from services.extractor.config import ORACLE_DSN


class OracleClient:
    def __init__(self, dsn: str):
        if not dsn:
            raise ValueError("ORACLE_DSN nao configurado")
        self._dsn = dsn

    def fetch_all(self, sql: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        try:
            import oracledb
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "Dependencia oracledb nao instalada. Adicione 'oracledb' no ambiente."
            ) from exc

        with oracledb.connect(dsn=self._dsn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql, params)
                columns = [c[0] for c in cursor.description]
                rows = cursor.fetchall()
        return [dict(zip(columns, row)) for row in rows]


def build_oracle_client() -> OracleClient:
    return OracleClient(dsn=ORACLE_DSN)
