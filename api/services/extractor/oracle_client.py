from __future__ import annotations

from typing import Any

from services.extractor.config import ORACLE_DSN
from services.extractor.oracle_dsn import parse_oracle_dsn
from services.extractor.oracle_init import ensure_oracle_client


class OracleClient:
    def __init__(self, dsn: str):
        self._config = parse_oracle_dsn(dsn)

    def fetch_all(self, sql: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        try:
            import oracledb
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "Dependencia oracledb nao instalada. Adicione 'oracledb' no ambiente."
            ) from exc

        ensure_oracle_client()

        if self._config["mode"] == "connect_string":
            connection = oracledb.connect(dsn=self._config["connect_string"])
        else:
            connection = oracledb.connect(
                user=self._config["user"],
                password=self._config["password"],
                host=self._config["host"],
                port=self._config["port"],
                service_name=self._config["service_name"],
            )

        with connection:
            with connection.cursor() as cursor:
                cursor.execute(sql, params)
                if cursor.description is None:
                    return []
                columns = [c[0] for c in cursor.description]
                rows = cursor.fetchall()
        return [dict(zip(columns, row)) for row in rows]


def build_oracle_client() -> OracleClient:
    return OracleClient(dsn=ORACLE_DSN)
