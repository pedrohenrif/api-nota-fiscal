from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol

from services.extractor.extraction_profiles import PROFILES
from services.extractor.note_validation import validate_note_row
from services.extractor.oracle_client import build_oracle_client
from services.extractor.schemas import NotaFiscalPRPayload
from services.extractor.sql_templates import (
    HEADER_NOTE_BY_NR_SEQUENCIA_SQL,
    LOTS_BY_ITEM_FALLBACK_SQL,
    LOTS_BY_ITEM_LOTE_SQL,
    build_header_notes_sql,
    build_items_by_nr_sequencia_sql,
)


class QueryExecutor(Protocol):
    def fetch_all(self, sql: str, params: dict[str, Any]) -> list[dict[str, Any]]: ...


def _g(row: dict[str, Any], key: str, default: Any = None) -> Any:
    return row.get(key, row.get(key.upper(), row.get(key.lower(), default)))


def _to_float(value: Any) -> float:
    if value is None:
        return 0.0
    return float(value)


def _to_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _as_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    return None


def _normalize_cnpj(value: Any) -> str:
    digits = "".join(ch for ch in _to_str(value) if ch.isdigit())
    return digits


def _fetch_note_items(
    db_client: QueryExecutor, nr_sequencia: Any, cd_operacao_nf_item_not_in: tuple[int, ...]
) -> list[dict[str, Any]]:
    items_sql = build_items_by_nr_sequencia_sql(cd_operacao_nf_item_not_in)
    return db_client.fetch_all(items_sql, params={"nr_sequencia": nr_sequencia})


def _fetch_item_lots(
    db_client: QueryExecutor, nr_sequencia: Any, nr_item_nf: Any
) -> list[dict[str, Any]]:
    params = {"nr_sequencia": nr_sequencia, "nr_item_nf": nr_item_nf}
    lots = db_client.fetch_all(LOTS_BY_ITEM_LOTE_SQL, params=params)
    if lots:
        return lots
    return db_client.fetch_all(LOTS_BY_ITEM_FALLBACK_SQL, params=params)


def _build_note_payload(
    estabelecimento: str,
    note_row: dict[str, Any],
    item_rows: list[dict[str, Any]],
    db_client: QueryExecutor,
) -> NotaFiscalPRPayload:
    products = []
    nr_sequencia = _g(note_row, "NR_SEQUENCIA")

    for item in item_rows:
        nr_item_nf = _g(item, "NR_ITEM_NF")
        lots_rows = _fetch_item_lots(
            db_client=db_client,
            nr_sequencia=nr_sequencia,
            nr_item_nf=nr_item_nf,
        )
        lots_payload = [
            {
                "lote": _to_str(_g(lot, "LOTE")),
                "validade": _as_datetime(_g(lot, "DT_VALIDADE")),
                "observacao": _to_str(_g(lot, "OBSERVACAO")) or None,
                "qtdLote": _to_float(_g(lot, "QT_LOTE")),
            }
            for lot in lots_rows
        ]

        products.append(
            {
                "codProd": _to_str(_g(item, "CODPROD")),
                "cunit": _to_float(_g(item, "CUNIT")),
                "valor": _to_float(_g(item, "VALOR")),
                "qtdEntrada": _to_float(_g(item, "QTDE_ENTRADA")),
                "loteNF": lots_payload,
            }
        )

    return NotaFiscalPRPayload(
        estabelecimento=estabelecimento,
        nrSequencia=_to_str(nr_sequencia),
        nf=_to_str(_g(note_row, "NF")),
        serie=_to_str(_g(note_row, "SERIE")),
        fornecedor={"cnpj": _normalize_cnpj(_g(note_row, "FORNECEDOR"))},
        dataNF=_as_datetime(_g(note_row, "DATANOTA")) or datetime.utcnow(),
        operador=_to_str(_g(note_row, "OPERADOR")) or "INTEGRACAO",
        doacao=_to_str(_g(note_row, "DOACAO")).upper() == "S",
        vencimento=_as_datetime(_g(note_row, "VENCIMENTO")),
        dataRecebimento=_as_datetime(_g(note_row, "DATAREC")),
        desconto=_to_float(_g(note_row, "DESCONTO")),
        ipi=_to_float(_g(note_row, "IPI")),
        frete=_to_float(_g(note_row, "FRETE")),
        valorTotal=_to_float(_g(note_row, "VALOR_TOTAL_NOTA")),
        qtdItens=len(products),
        produtos=products,
    )


def extract_pending_notes(
    estabelecimento: str, db_client: QueryExecutor | None = None
) -> list[NotaFiscalPRPayload]:
    if estabelecimento not in PROFILES:
        raise ValueError(f"Estabelecimento nao mapeado: {estabelecimento}")

    profile = PROFILES[estabelecimento]
    oracle = db_client or build_oracle_client()
    header_sql = build_header_notes_sql(profile.cd_operacao_nf_in)

    note_rows = oracle.fetch_all(
        header_sql,
        params={
            "dt_atualizacao_estoque_min": profile.dt_atualizacao_estoque_min,
            "dt_emissao_min": profile.dt_emissao_min,
            "cd_estabelecimento": profile.cd_estabelecimento,
        },
    )

    payloads = []
    for note_row in note_rows:
        nr_sequencia = _g(note_row, "NR_SEQUENCIA")
        item_rows = _fetch_note_items(
            db_client=oracle,
            nr_sequencia=nr_sequencia,
            cd_operacao_nf_item_not_in=profile.cd_operacao_nf_item_not_in,
        )
        payloads.append(
            _build_note_payload(
                estabelecimento=estabelecimento,
                note_row=note_row,
                item_rows=item_rows,
                db_client=oracle,
            )
        )
    return payloads


def _fetch_note_header_by_nr_sequencia(
    db_client: QueryExecutor, nr_sequencia: str | int
) -> dict[str, Any] | None:
    rows = db_client.fetch_all(
        HEADER_NOTE_BY_NR_SEQUENCIA_SQL,
        params={"nr_sequencia": nr_sequencia},
    )
    if not rows:
        return None
    return rows[0]


def consult_note_by_nr_sequencia(
    estabelecimento: str,
    nr_sequencia: str | int,
    db_client: QueryExecutor | None = None,
) -> dict[str, Any]:
    if estabelecimento not in PROFILES:
        raise ValueError(f"Estabelecimento nao mapeado: {estabelecimento}")

    profile = PROFILES[estabelecimento]
    oracle = db_client or build_oracle_client()
    note_row = _fetch_note_header_by_nr_sequencia(oracle, nr_sequencia)

    if note_row is None:
        return {
            "encontrada": False,
            "valido": False,
            "mensagem": f"Nota com nr_sequencia {nr_sequencia} nao encontrada.",
            "nr_sequencia": str(nr_sequencia),
            "operacoes_liberadas": list(profile.cd_operacao_nf_in),
        }

    validation = validate_note_row(note_row, profile)
    item_rows = _fetch_note_items(
        db_client=oracle,
        nr_sequencia=_g(note_row, "NR_SEQUENCIA"),
        cd_operacao_nf_item_not_in=profile.cd_operacao_nf_item_not_in,
    )

    resposta: dict[str, Any] = {
        "encontrada": True,
        "valido": validation.valido,
        "mensagem": validation.mensagem,
        "nr_sequencia": _to_str(_g(note_row, "NR_SEQUENCIA")),
        "nf": _to_str(_g(note_row, "NF")),
        "cd_operacao_nf": validation.cd_operacao_nf,
        "operacoes_liberadas": list(validation.operacoes_liberadas),
        "fornecedor": _normalize_cnpj(_g(note_row, "FORNECEDOR")),
        "data_nf": _as_datetime(_g(note_row, "DATANOTA")),
        "qtd_itens": len(item_rows),
    }

    if validation.valido and item_rows:
        resposta["preview"] = _build_note_payload(
            estabelecimento=estabelecimento,
            note_row=note_row,
            item_rows=item_rows,
            db_client=oracle,
        ).model_dump(mode="json")
    elif validation.valido and not item_rows:
        resposta["valido"] = False
        resposta["mensagem"] = "Nota sem itens elegiveis para integracao."

    return resposta


def extract_single_note(
    estabelecimento: str,
    nr_sequencia: str | int,
    db_client: QueryExecutor | None = None,
) -> NotaFiscalPRPayload:
    consulta = consult_note_by_nr_sequencia(
        estabelecimento=estabelecimento,
        nr_sequencia=nr_sequencia,
        db_client=db_client,
    )
    if not consulta.get("encontrada"):
        raise ValueError(consulta["mensagem"])
    if not consulta.get("valido"):
        raise ValueError(consulta.get("mensagem") or "Nota nao elegivel para emissao.")

    preview = consulta.get("preview")
    if not preview:
        raise ValueError("Nota sem payload valido para publicacao.")

    return NotaFiscalPRPayload.model_validate(preview)


class MockOracleClient:
    def fetch_all(self, sql: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        cd_estab = params.get("cd_estabelecimento", 8)

        if "nf.nr_sequencia = :nr_sequencia" in sql and "CD_OPERACAO_NF" in sql:
            nr_seq = params.get("nr_sequencia")
            if str(nr_seq) == "999002":
                return [
                    {
                        "NF": "654321",
                        "FORNECEDOR": "98.765.432/0001-10",
                        "DATANOTA": datetime.utcnow(),
                        "OPERADOR": "INTEGRACAO",
                        "DOACAO": "N",
                        "SERIE": "1",
                        "DATAREC": datetime.utcnow(),
                        "DESCONTO": 0,
                        "IPI": 0,
                        "FRETE": 0,
                        "NR_SEQUENCIA": 999002,
                        "VALOR_TOTAL_NOTA": 100,
                        "VENCIMENTO": datetime.utcnow(),
                        "CD_OPERACAO_NF": 33,
                        "CD_ESTABELECIMENTO": cd_estab,
                        "IE_SITUACAO": 1,
                        "DT_INTEGRACAO": None,
                        "IE_TIPO_NOTA": "EN",
                        "DT_ATUALIZACAO_ESTOQUE": datetime.utcnow(),
                    }
                ]
            if str(nr_seq) in ("999001", "12345"):
                return [
                    {
                        "NF": "123456",
                        "FORNECEDOR": "12.345.678/9123-45",
                        "DATANOTA": datetime.utcnow(),
                        "OPERADOR": "INTEGRACAO",
                        "DOACAO": "N",
                        "SERIE": "1",
                        "DATAREC": datetime.utcnow(),
                        "DESCONTO": 0,
                        "IPI": 0,
                        "FRETE": 0,
                        "NR_SEQUENCIA": int(nr_seq) if str(nr_seq).isdigit() else nr_seq,
                        "VALOR_TOTAL_NOTA": 400,
                        "VENCIMENTO": datetime.utcnow(),
                        "CD_OPERACAO_NF": 1,
                        "CD_ESTABELECIMENTO": cd_estab,
                        "IE_SITUACAO": 1,
                        "DT_INTEGRACAO": None,
                        "IE_TIPO_NOTA": "EN",
                        "DT_ATUALIZACAO_ESTOQUE": datetime.utcnow(),
                    }
                ]
            return []

        if "MAX(nfv.dt_vencimento)" in sql:
            return [
                {
                    "NF": "123456",
                    "FORNECEDOR": "12.345.678/9123-45",
                    "DATANOTA": datetime.utcnow(),
                    "OPERADOR": "INTEGRACAO",
                    "DOACAO": "N",
                    "SERIE": "1",
                    "DATAREC": datetime.utcnow(),
                    "DESCONTO": 0,
                    "IPI": 0,
                    "FRETE": 0,
                    "NR_SEQUENCIA": 999001,
                    "VALOR_TOTAL_NOTA": 400,
                    "VENCIMENTO": datetime.utcnow(),
                }
            ]
        if "nfi.vl_unitario_item_nf" in sql:
            return [
                {
                    "CODPROD": "63437",
                    "CUNIT": 200,
                    "VALOR": 400,
                    "QTDE_ENTRADA": 2,
                    "NR_SEQ_NOTA": params.get("nr_sequencia"),
                    "NR_ITEM_NF": 1,
                    "DS_REDUZIDA": "ITEM TESTE",
                    "VL_LIQUIDO": 400,
                }
            ]
        if "nota_fiscal_item_lote" in sql or "qt_item_nf" in sql:
            return [
                {
                    "LOTE": "A01",
                    "DT_VALIDADE": datetime.utcnow(),
                    "OBSERVACAO": "Nome Lab 1",
                    "QT_LOTE": 1,
                },
                {
                    "LOTE": "A02",
                    "DT_VALIDADE": datetime.utcnow(),
                    "OBSERVACAO": "Nome Lab 2",
                    "QT_LOTE": 1,
                },
            ]
        return []
