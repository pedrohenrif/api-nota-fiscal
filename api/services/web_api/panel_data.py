from datetime import date
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

_BASE_QUERY = """
SELECT
    id,
    estabelecimento,
    nf,
    nr_sequencia,
    fornecedor,
    data_nf,
    status,
    tentativas,
    erro,
    created_at,
    updated_at
FROM nota_processamento
"""


def list_notas(
    db: Session,
    estabelecimento: Optional[str] = None,
    nf: Optional[str] = None,
    nr_sequencia: Optional[str] = None,
    fornecedor: Optional[str] = None,
    status: Optional[str] = None,
    data_nf_inicio: Optional[date] = None,
    data_nf_fim: Optional[date] = None,
    limit: int = 200,
) -> list[dict]:
    conditions: list[str] = []
    params: dict = {"limit": limit}

    if estabelecimento:
        conditions.append("estabelecimento = :estabelecimento")
        params["estabelecimento"] = estabelecimento
    if nf:
        conditions.append("nf ILIKE :nf")
        params["nf"] = f"%{nf.strip()}%"
    if nr_sequencia:
        conditions.append("nr_sequencia ILIKE :nr_sequencia")
        params["nr_sequencia"] = f"%{nr_sequencia.strip()}%"
    if fornecedor:
        conditions.append("fornecedor ILIKE :fornecedor")
        params["fornecedor"] = f"%{fornecedor.strip()}%"
    if status:
        conditions.append("status = :status")
        params["status"] = status.strip()
    if data_nf_inicio:
        conditions.append("DATE(data_nf) >= :data_nf_inicio")
        params["data_nf_inicio"] = data_nf_inicio
    if data_nf_fim:
        conditions.append("DATE(data_nf) <= :data_nf_fim")
        params["data_nf_fim"] = data_nf_fim

    sql = _BASE_QUERY
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY updated_at DESC NULLS LAST, id DESC LIMIT :limit"

    rows = db.execute(text(sql), params).mappings().all()
    return [dict(row) for row in rows]


def get_nota_by_id(db: Session, nota_id: int) -> dict | None:
    sql = _BASE_QUERY + " WHERE id = :id LIMIT 1"
    row = db.execute(text(sql), {"id": nota_id}).mappings().first()
    return dict(row) if row else None
