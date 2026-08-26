from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from sqlalchemy import text

from services.common.estab_config import SessionLocal
from services.extractor.extraction_profiles import PROFILES
from services.extractor.extractor import (
    MockOracleClient,
    _fetch_item_lots,
    _fetch_note_items,
    _g,
    _to_float,
    _to_str,
)
from services.extractor.oracle_client import build_oracle_client
from services.extractor.sql_templates import build_header_notes_sql
from services.processor.config import build_pr_auth_headers, get_pr_config
from services.processor.depara import check_product_depara
from services.report.config import REPORT_LOOKBACK_MINUTES, USE_MOCK_ORACLE
from services.report.report_sent import filter_unreported


def _oracle_client():
    return MockOracleClient() if USE_MOCK_ORACLE else build_oracle_client()


def _fetch_middleware_sent(estabelecimento: str, since: datetime) -> dict[str, dict]:
    sql = text(
        """
        SELECT nr_sequencia, nf, status, pr_id, pr_mensagem, updated_at
        FROM nota_processamento
        WHERE estabelecimento = :estabelecimento
          AND status = 'sent'
          AND updated_at >= :since
        ORDER BY updated_at DESC
        """
    )
    db = SessionLocal()
    try:
        rows = db.execute(
            sql, {"estabelecimento": estabelecimento, "since": since}
        ).mappings().all()
        result: dict[str, dict] = {}
        for row in rows:
            key = str(row.get("nr_sequencia") or row.get("nf") or "")
            if key and key not in result:
                result[key] = dict(row)
        return result
    finally:
        db.close()


def _fetch_middleware_errors(estabelecimento: str, since: datetime) -> list[dict[str, Any]]:
    sql = text(
        """
        SELECT nr_sequencia, nf, status, erro, pr_mensagem, updated_at
        FROM nota_processamento
        WHERE estabelecimento = :estabelecimento
          AND status IN ('dead_letter', 'retry_pending')
          AND updated_at >= :since
        ORDER BY updated_at DESC
        LIMIT 100
        """
    )
    db = SessionLocal()
    try:
        rows = db.execute(
            sql, {"estabelecimento": estabelecimento, "since": since}
        ).mappings().all()
        return [
            {
                "nr_sequencia": row.get("nr_sequencia"),
                "nf": row.get("nf"),
                "status": row.get("status"),
                "erro": row.get("erro") or row.get("pr_mensagem") or "",
            }
            for row in rows
        ]
    finally:
        db.close()


def _fetch_all_sent_keys(estabelecimento: str) -> set[str]:
    sql = text(
        """
        SELECT nr_sequencia, nf
        FROM nota_processamento
        WHERE estabelecimento = :estabelecimento
          AND status = 'sent'
        """
    )
    db = SessionLocal()
    try:
        rows = db.execute(sql, {"estabelecimento": estabelecimento}).mappings().all()
        keys: set[str] = set()
        for row in rows:
            if row.get("nr_sequencia"):
                keys.add(str(row["nr_sequencia"]))
            if row.get("nf"):
                keys.add(str(row["nf"]))
        return keys
    finally:
        db.close()


def classify_estabelecimento(estabelecimento: str) -> dict[str, Any]:
    if estabelecimento not in PROFILES:
        raise ValueError(f"Estabelecimento nao mapeado: {estabelecimento}")

    since = datetime.now(timezone.utc) - timedelta(minutes=max(REPORT_LOOKBACK_MINUTES, 1))
    profile = PROFILES[estabelecimento]
    oracle = _oracle_client()
    header_sql = build_header_notes_sql(profile.cd_operacao_nf_in)
    note_rows = oracle.fetch_all(
        header_sql,
        params={
            "dt_atualizacao_estoque_min": profile.dt_atualizacao_estoque_min,
            "dt_emissao_min": profile.dt_emissao_min,
            "cd_estabelecimento": profile.cd_estabelecimento,
        },
    )

    sent_recent = _fetch_middleware_sent(estabelecimento, since)
    sent_all_keys = _fetch_all_sent_keys(estabelecimento)
    erros_pr = _fetch_middleware_errors(estabelecimento, since)

    integradas: list[dict[str, Any]] = []
    for key, row in sent_recent.items():
        integradas.append(
            {
                "nr_sequencia": row.get("nr_sequencia") or key,
                "nf": row.get("nf"),
                "valor_total": None,
                "pr_id": row.get("pr_id"),
            }
        )

    # Enriquecer valor_total das integradas a partir do Oracle, se a nota ainda estiver na lista.
    valor_by_seq = {
        _to_str(_g(r, "NR_SEQUENCIA")): _to_float(_g(r, "VALOR_TOTAL_NOTA"))
        for r in note_rows
    }
    for item in integradas:
        seq = str(item.get("nr_sequencia") or "")
        if seq in valor_by_seq:
            item["valor_total"] = valor_by_seq[seq]

    # Integradas / erros PR: so entram no e-mail uma vez (apos o primeiro envio).
    integradas = filter_unreported(estabelecimento, "integradas", integradas)
    erros_pr = filter_unreported(estabelecimento, "erros_pr", erros_pr)

    nao_integradas: list[dict[str, Any]] = []
    sem_depara: list[dict[str, Any]] = []
    sem_lote: list[dict[str, Any]] = []

    pr_config = get_pr_config(estabelecimento)

    with httpx.Client(timeout=30.0) as client:
        for note_row in note_rows:
            nr_sequencia = _to_str(_g(note_row, "NR_SEQUENCIA"))
            nf = _to_str(_g(note_row, "NF"))
            valor = _to_float(_g(note_row, "VALOR_TOTAL_NOTA"))

            if nr_sequencia in sent_all_keys or nf in sent_all_keys:
                continue

            item_rows = _fetch_note_items(
                db_client=oracle,
                nr_sequencia=nr_sequencia,
                cd_operacao_nf_item_not_in=profile.cd_operacao_nf_item_not_in,
            )

            itens_sem_depara: list[str] = []
            desc_sem_depara: list[str] = []
            itens_sem_lote: list[str] = []

            for item in item_rows:
                cod = _to_str(_g(item, "CODPROD"))
                ds = _to_str(_g(item, "DS_REDUZIDA")) or "—"
                depara = check_product_depara(
                    client=client,
                    base_url=pr_config["base_url"],
                    token=pr_config["token"],
                    cod_material=cod,
                )
                if depara["status"] != "ok":
                    itens_sem_depara.append(cod)
                    desc_sem_depara.append(ds)
                    continue

                # So exige lote completo quando o PR marca ControleDeLote=true.
                if depara.get("controleDeLote"):
                    nr_item = _g(item, "NR_ITEM_NF")
                    lots = _fetch_item_lots(oracle, nr_sequencia, nr_item)
                    has_lote_completo = any(
                        _to_str(_g(lot, "LOTE")) and _g(lot, "DT_VALIDADE") is not None
                        for lot in lots
                    )
                    if not has_lote_completo:
                        itens_sem_lote.append(
                            f"Item {nr_item} (material {cod}) exige lote/validade no PR"
                        )

            # Prioridade exclusiva: sem de-para > sem lote > nao integrada.
            # Evita a mesma nota aparecer em mais de uma secao do e-mail.
            if itens_sem_depara:
                sem_depara.append(
                    {
                        "nr_sequencia": nr_sequencia,
                        "nf": nf,
                        "valor_total": valor,
                        "itens": itens_sem_depara,
                        "descricoes": desc_sem_depara,
                    }
                )
            elif itens_sem_lote:
                for msg in itens_sem_lote:
                    sem_lote.append(
                        {
                            "nr_sequencia": nr_sequencia,
                            "nf": nf,
                            "inconsistencia": msg,
                        }
                    )
            else:
                nao_integradas.append(
                    {
                        "nr_sequencia": nr_sequencia,
                        "nf": nf,
                        "valor_total": valor,
                    }
                )

    nao_integradas = filter_unreported(estabelecimento, "nao_integradas", nao_integradas)

    return {
        "estabelecimento": estabelecimento,
        "integradas": integradas,
        "nao_integradas": nao_integradas,
        "sem_depara": sem_depara,
        "sem_lote": sem_lote,
        "erros_pr": erros_pr,
        "totais": {
            "integradas": len(integradas),
            "nao_integradas": len(nao_integradas),
            "sem_depara": len(sem_depara),
            "sem_lote": len(sem_lote),
            "erros_pr": len(erros_pr),
        },
    }


def has_report_content(report: dict[str, Any]) -> bool:
    """Dispara e-mail automatico so com pendencias/erros.

    Notas ja emitidas (integradas/sent) nao disparam o ciclo sozinhas.
    """
    totais = report.get("totais") or {}
    problem_keys = ("nao_integradas", "sem_depara", "sem_lote", "erros_pr")
    return any(int(totais.get(key, 0) or 0) > 0 for key in problem_keys)
