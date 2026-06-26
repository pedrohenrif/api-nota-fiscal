from __future__ import annotations

from urllib.parse import parse_qs, unquote, urlparse


def parse_oracle_dsn(dsn: str) -> dict:
    """
    Aceita:
    - URL estilo SQLAlchemy: oracle+cx_oracle://user:pass@host:port/?service_name=XXX
    - String de conexao Oracle nativa (DESCRIPTION=... ou Easy Connect)
    """
    raw = dsn.strip()
    if not raw:
        raise ValueError("ORACLE_DSN nao configurado")

    if raw.startswith("oracle"):
        normalized = raw.replace("oracle+cx_oracle://", "oracle://", 1)
        normalized = normalized.replace("oracle+oracledb://", "oracle://", 1)
        parsed = urlparse(normalized)
        if not parsed.hostname:
            raise ValueError("ORACLE_DSN invalido: host ausente na URL")

        query = parse_qs(parsed.query)
        service_name = (
            query.get("service_name", [None])[0]
            or query.get("service", [None])[0]
            or parsed.path.lstrip("/")
            or None
        )
        if not service_name:
            raise ValueError(
                "ORACLE_DSN invalido: informe service_name na query (?service_name=...)"
            )

        return {
            "mode": "params",
            "user": unquote(parsed.username or ""),
            "password": unquote(parsed.password or ""),
            "host": parsed.hostname,
            "port": parsed.port or 1521,
            "service_name": service_name,
        }

    return {"mode": "connect_string", "connect_string": raw}
