from __future__ import annotations

from typing import Any

from services.hrba_processor import queries
from services.hrba_processor.oracle_session import OracleSession


def _row_upper(row: dict[str, Any]) -> dict[str, Any]:
    return {str(k).upper(): v for k, v in row.items()}


def carregar_nota_sede(sede: OracleSession, nr_sequencia: str | int) -> dict[str, Any] | None:
    headers = sede.fetch_all(queries.SELECT_NOTA_HEADER, {"nr_sequencia": nr_sequencia})
    if not headers:
        return None

    nota = _row_upper(headers[0])
    nota["ITENS_SEM_DEPARA"] = []
    nota["INCONSISTENCIA_PROCEDURE"] = []
    nota["NOTA_FISCAL_VENC"] = [
        _row_upper(r) for r in sede.fetch_all(queries.SELECT_NOTA_VENC, {"nr_sequencia": nr_sequencia})
    ]
    nota["NOTA_FISCAL_ITEM"] = [
        _row_upper(r) for r in sede.fetch_all(queries.SELECT_NOTA_ITEM, {"nr_sequencia": nr_sequencia})
    ]
    nota["NOTA_FISCAL_ITEM_LOTE"] = [
        _row_upper(r)
        for r in sede.fetch_all(queries.SELECT_NF_ITEM_LOTE, {"nr_sequencia": nr_sequencia})
    ]
    return nota
