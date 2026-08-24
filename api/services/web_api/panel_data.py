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

_ORDER_BY = {
    "nr_sequencia": """
ORDER BY
  CASE
    WHEN nr_sequencia ~ '^[0-9]+$' THEN nr_sequencia::bigint
    ELSE NULL
  END DESC NULLS LAST,
  id DESC
""",
    "data_nf": """
ORDER BY
  data_nf DESC NULLS LAST,
  id DESC
""",
}


def _order_clause(ordenacao: str | None) -> str:
    key = (ordenacao or "nr_sequencia").strip().lower()
    return _ORDER_BY.get(key, _ORDER_BY["nr_sequencia"])


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
    ordenacao: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
) -> dict:
    page = max(int(page or 1), 1)
    page_size = min(max(int(page_size or 50), 1), 200)
    offset = (page - 1) * page_size
    order_sql = _order_clause(ordenacao)

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
            text(f"{_BASE_SELECT}{where} {order_sql} LIMIT :limit OFFSET :offset"),
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
    ordenacao: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
) -> dict:
    page = max(int(page or 1), 1)
    page_size = min(max(int(page_size or 50), 1), 200)
    offset = (page - 1) * page_size
    order_sql = _order_clause(ordenacao)

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
            text(f"{_BASE_SELECT}{where} {order_sql} LIMIT :limit OFFSET :offset"),
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


def update_nota_metadata(
    db: Session,
    nota_id: int,
    *,
    nf: str | None = None,
    fornecedor: str | None = None,
    data_nf=None,
) -> dict | None:
    """Atualiza metadados espelhados do Tasy no banco auxiliar."""
    sets: list[str] = ["updated_at = NOW()"]
    params: dict = {"id": nota_id}
    if nf is not None and str(nf).strip():
        sets.append("nf = :nf")
        params["nf"] = str(nf).strip()
    if fornecedor is not None:
        sets.append("fornecedor = :fornecedor")
        params["fornecedor"] = str(fornecedor).strip() or None
    if data_nf is not None:
        sets.append("data_nf = :data_nf")
        params["data_nf"] = data_nf

    sql = text(
        f"UPDATE nota_processamento SET {', '.join(sets)} WHERE id = :id"
    )
    result = db.execute(sql, params)
    db.commit()
    if result.rowcount == 0:
        return None
    return get_nota_by_id(db, nota_id)


def _dashboard_where(
    *,
    estabelecimento: Optional[str] = None,
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    usar_data_nf: bool = False,
) -> tuple[str, dict]:
    conditions: list[str] = []
    params: dict = {}
    if estabelecimento:
        conditions.append("estabelecimento = :estabelecimento")
        params["estabelecimento"] = estabelecimento
    date_col = "data_nf" if usar_data_nf else "updated_at"
    if data_inicio:
        conditions.append(f"DATE({date_col}) >= :data_inicio")
        params["data_inicio"] = data_inicio
    if data_fim:
        conditions.append(f"DATE({date_col}) <= :data_fim")
        params["data_fim"] = data_fim
    where = (" WHERE " + " AND ".join(conditions)) if conditions else ""
    return where, params


def dashboard_resumo(
    db: Session,
    *,
    estabelecimento: Optional[str] = None,
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    usar_data_nf: bool = False,
) -> dict:
    where, params = _dashboard_where(
        estabelecimento=estabelecimento,
        data_inicio=data_inicio,
        data_fim=data_fim,
        usar_data_nf=usar_data_nf,
    )

    total = int(
        db.execute(
            text(f"SELECT COUNT(*) FROM nota_processamento{where}"), params
        ).scalar()
        or 0
    )

    por_status_rows = db.execute(
        text(
            f"""
            SELECT status, COUNT(*) AS qtd
            FROM nota_processamento
            {where}
            GROUP BY status
            ORDER BY qtd DESC
            """
        ),
        params,
    ).mappings().all()
    por_status = {str(r["status"]): int(r["qtd"]) for r in por_status_rows}

    sent = int(por_status.get("sent", 0))
    retry = int(por_status.get("retry_pending", 0))
    dead = int(por_status.get("dead_letter", 0))
    pending = int(por_status.get("pending", 0))
    com_erro = retry + dead
    taxa_sucesso = round((sent / total) * 100, 1) if total else 0.0
    taxa_erro = round((com_erro / total) * 100, 1) if total else 0.0

    erro_where = where + (" AND " if where else " WHERE ") + "erro_tipo IS NOT NULL"
    por_erro_rows = db.execute(
        text(
            f"""
            SELECT erro_tipo, COUNT(*) AS qtd
            FROM nota_processamento
            {erro_where}
            GROUP BY erro_tipo
            ORDER BY qtd DESC
            """
        ),
        params,
    ).mappings().all()
    por_erro_tipo = [
        {"erro_tipo": str(r["erro_tipo"]), "qtd": int(r["qtd"])} for r in por_erro_rows
    ]

    por_estab_rows = db.execute(
        text(
            f"""
            SELECT
              estabelecimento,
              COUNT(*) AS total,
              COUNT(*) FILTER (WHERE status = 'sent') AS sent,
              COUNT(*) FILTER (WHERE status = 'retry_pending') AS retry_pending,
              COUNT(*) FILTER (WHERE status = 'dead_letter') AS dead_letter,
              COUNT(*) FILTER (WHERE status = 'pending') AS pending
            FROM nota_processamento
            {where}
            GROUP BY estabelecimento
            ORDER BY total DESC
            """
        ),
        params,
    ).mappings().all()
    por_estabelecimento = [dict(r) for r in por_estab_rows]

    date_col = "data_nf" if usar_data_nf else "updated_at"
    serie_rows = db.execute(
        text(
            f"""
            SELECT
              DATE({date_col}) AS dia,
              COUNT(*) FILTER (WHERE status = 'sent') AS sent,
              COUNT(*) FILTER (
                WHERE status IN ('retry_pending', 'dead_letter')
              ) AS erros,
              COUNT(*) AS total
            FROM nota_processamento
            {where}
            GROUP BY DATE({date_col})
            ORDER BY dia DESC NULLS LAST
            LIMIT 30
            """
        ),
        params,
    ).mappings().all()
    serie_diaria = [
        {
            "dia": str(r["dia"]) if r["dia"] is not None else None,
            "sent": int(r["sent"] or 0),
            "erros": int(r["erros"] or 0),
            "total": int(r["total"] or 0),
        }
        for r in reversed(list(serie_rows))
    ]

    recentes_erro_where = (
        where
        + (" AND " if where else " WHERE ")
        + "status IN ('retry_pending', 'dead_letter')"
    )
    recentes_rows = db.execute(
        text(
            f"""
            {_BASE_SELECT}
            {recentes_erro_where}
            ORDER BY updated_at DESC NULLS LAST, id DESC
            LIMIT 15
            """
        ),
        params,
    ).mappings().all()

    return {
        "filtros": {
            "estabelecimento": estabelecimento,
            "data_inicio": data_inicio.isoformat() if data_inicio else None,
            "data_fim": data_fim.isoformat() if data_fim else None,
            "usar_data_nf": usar_data_nf,
        },
        "kpis": {
            "total": total,
            "sent": sent,
            "retry_pending": retry,
            "dead_letter": dead,
            "pending": pending,
            "com_erro": com_erro,
            "taxa_sucesso_pct": taxa_sucesso,
            "taxa_erro_pct": taxa_erro,
        },
        "por_status": [
            {"status": k, "qtd": v} for k, v in sorted(por_status.items(), key=lambda x: -x[1])
        ],
        "por_erro_tipo": por_erro_tipo,
        "por_estabelecimento": por_estabelecimento,
        "serie_diaria": serie_diaria,
        "recentes_com_erro": [dict(r) for r in recentes_rows],
    }


def list_notas_export(
    db: Session,
    *,
    estabelecimento: Optional[str] = None,
    status: Optional[str] = None,
    erro_tipo: Optional[str] = None,
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    usar_data_nf: bool = False,
    limit: int = 10000,
) -> list[dict]:
    conditions, params = _build_filters(
        estabelecimento=estabelecimento,
        status=status,
        erro_tipo=erro_tipo,
    )
    date_col = "data_nf" if usar_data_nf else "updated_at"
    if data_inicio:
        conditions.append(f"DATE({date_col}) >= :data_inicio")
        params["data_inicio"] = data_inicio
    if data_fim:
        conditions.append(f"DATE({date_col}) <= :data_fim")
        params["data_fim"] = data_fim

    where = (" WHERE " + " AND ".join(conditions)) if conditions else ""
    params["limit"] = min(max(int(limit or 10000), 1), 50000)
    rows = (
        db.execute(
            text(
                f"""
                {_BASE_SELECT}
                {where}
                ORDER BY updated_at DESC NULLS LAST, id DESC
                LIMIT :limit
                """
            ),
            params,
        )
        .mappings()
        .all()
    )
    return [dict(row) for row in rows]
