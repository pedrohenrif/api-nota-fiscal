from datetime import date
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

_BASE_SELECT = """
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
    erro_tipo,
    pr_id,
    pr_mensagem,
    created_at,
    updated_at
FROM nota_processamento
"""

_ORDER_NR_SEQUENCIA_DESC = """
ORDER BY
  CASE
    WHEN nr_sequencia ~ '^[0-9]+$' THEN nr_sequencia::bigint
    ELSE NULL
  END DESC NULLS LAST,
  id DESC
"""


def _build_filters(
    *,
    estabelecimento: Optional[str] = None,
    nf: Optional[str] = None,
    nr_sequencia: Optional[str] = None,
    fornecedor: Optional[str] = None,
    status: Optional[str] = None,
    erro_tipo: Optional[str] = None,
    data_nf_inicio: Optional[date] = None,
    data_nf_fim: Optional[date] = None,
) -> tuple[list[str], dict]:
    conditions: list[str] = []
    params: dict = {}

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
    if erro_tipo:
        conditions.append("erro_tipo = :erro_tipo")
        params["erro_tipo"] = erro_tipo.strip()
    if data_nf_inicio:
        conditions.append("DATE(data_nf) >= :data_nf_inicio")
        params["data_nf_inicio"] = data_nf_inicio
    if data_nf_fim:
        conditions.append("DATE(data_nf) <= :data_nf_fim")
        params["data_nf_fim"] = data_nf_fim

    return conditions, params


def list_notas(
    db: Session,
    estabelecimento: Optional[str] = None,
    nf: Optional[str] = None,
    nr_sequencia: Optional[str] = None,
    fornecedor: Optional[str] = None,
    status: Optional[str] = None,
    erro_tipo: Optional[str] = None,
    data_nf_inicio: Optional[date] = None,
    data_nf_fim: Optional[date] = None,
    page: int = 1,
    page_size: int = 50,
) -> dict:
    page = max(int(page or 1), 1)
    page_size = min(max(int(page_size or 50), 1), 200)
    offset = (page - 1) * page_size

    conditions, params = _build_filters(
        estabelecimento=estabelecimento,
        nf=nf,
        nr_sequencia=nr_sequencia,
        fornecedor=fornecedor,
        status=status,
        erro_tipo=erro_tipo,
        data_nf_inicio=data_nf_inicio,
        data_nf_fim=data_nf_fim,
    )
    where = (" WHERE " + " AND ".join(conditions)) if conditions else ""

    total = db.execute(
        text(f"SELECT COUNT(*) AS total FROM nota_processamento{where}"),
        params,
    ).scalar()
    total_int = int(total or 0)

    params_page = {**params, "limit": page_size, "offset": offset}
    rows = (
        db.execute(
            text(
                f"{_BASE_SELECT}{where} {_ORDER_NR_SEQUENCIA_DESC} LIMIT :limit OFFSET :offset"
            ),
            params_page,
        )
        .mappings()
        .all()
    )

    return {
        "items": [dict(row) for row in rows],
        "total": total_int,
        "page": page,
        "page_size": page_size,
        "total_pages": max((total_int + page_size - 1) // page_size, 1) if total_int else 0,
    }


def list_logs(
    db: Session,
    estabelecimento: Optional[str] = None,
    status: Optional[str] = None,
    erro_tipo: Optional[str] = None,
    somente_erro: bool = True,
    page: int = 1,
    page_size: int = 50,
) -> dict:
    page = max(int(page or 1), 1)
    page_size = min(max(int(page_size or 50), 1), 200)
    offset = (page - 1) * page_size

    conditions, params = _build_filters(
        estabelecimento=estabelecimento,
        status=status,
        erro_tipo=erro_tipo,
    )
    if somente_erro:
        conditions.append("erro IS NOT NULL AND TRIM(erro) <> ''")

    where = (" WHERE " + " AND ".join(conditions)) if conditions else ""

    total = db.execute(
        text(f"SELECT COUNT(*) AS total FROM nota_processamento{where}"),
        params,
    ).scalar()
    total_int = int(total or 0)

    params_page = {**params, "limit": page_size, "offset": offset}
    rows = (
        db.execute(
            text(
                f"{_BASE_SELECT}{where} {_ORDER_NR_SEQUENCIA_DESC} LIMIT :limit OFFSET :offset"
            ),
            params_page,
        )
        .mappings()
        .all()
    )

    return {
        "items": [dict(row) for row in rows],
        "total": total_int,
        "page": page,
        "page_size": page_size,
        "total_pages": max((total_int + page_size - 1) // page_size, 1) if total_int else 0,
    }


def get_nota_by_id(db: Session, nota_id: int) -> dict | None:
    sql = _BASE_SELECT + " WHERE id = :id LIMIT 1"
    row = db.execute(text(sql), {"id": nota_id}).mappings().first()
    return dict(row) if row else None
