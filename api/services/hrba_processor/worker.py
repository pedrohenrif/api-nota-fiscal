from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from services.hrba_processor.config import (
    ESTABELECIMENTO_NOME,
    ORACLE_SEDE_DSN,
    USE_MOCK_ORACLE,
    get_hrba_dsn,
)
from services.hrba_processor.depara import validar_nota
from services.hrba_processor.integracao import integrar_nota
from services.hrba_processor.loader import carregar_nota_sede
from services.hrba_processor.oracle_session import OracleSession
from services.processor.db import SessionLocal
from services.processor.repository import upsert_processing_status

logger = logging.getLogger(__name__)


def _payload_meta(payload: dict[str, Any]) -> dict[str, Any]:
    nr_sequencia = payload.get("nrSequencia") or payload.get("nr_sequencia")
    nf = payload.get("nf") or payload.get("NF") or ""
    fornecedor = None
    fornecedor_obj = payload.get("fornecedor")
    if isinstance(fornecedor_obj, dict):
        fornecedor = fornecedor_obj.get("cnpj")
    elif fornecedor_obj:
        fornecedor = str(fornecedor_obj)
    data_nf = payload.get("dataNF") or payload.get("data_nf")
    if isinstance(data_nf, str):
        try:
            data_nf = datetime.fromisoformat(data_nf.replace("Z", "+00:00"))
        except ValueError:
            data_nf = None
    return {
        "nr_sequencia": str(nr_sequencia) if nr_sequencia is not None else None,
        "nf": str(nf),
        "fornecedor": fornecedor,
        "data_nf": data_nf,
    }


def process_hrba_payload(payload: dict[str, Any]) -> str:
    """
    Processa uma mensagem da fila nf.hrba.raw.
    Retorna status final gravado no Postgres.
    """
    meta = _payload_meta(payload)
    nr_sequencia = meta["nr_sequencia"]
    if not nr_sequencia:
        raise ValueError("Payload HRBA sem nrSequencia")

    tentativas = int(payload.get("_retry_count", 0)) + 1
    db = SessionLocal()
    sede: OracleSession | None = None
    hrba: OracleSession | None = None

    try:
        upsert_processing_status(
            db,
            estabelecimento=ESTABELECIMENTO_NOME,
            nf=meta["nf"] or nr_sequencia,
            status="pending",
            tentativas=tentativas,
            nr_sequencia=nr_sequencia,
            fornecedor=meta["fornecedor"],
            data_nf=meta["data_nf"],
            pr_mensagem="Processando integracao SEDE -> HRBA",
        )

        if USE_MOCK_ORACLE:
            upsert_processing_status(
                db,
                estabelecimento=ESTABELECIMENTO_NOME,
                nf=meta["nf"] or nr_sequencia,
                status="sent",
                tentativas=tentativas,
                nr_sequencia=nr_sequencia,
                fornecedor=meta["fornecedor"],
                data_nf=meta["data_nf"],
                pr_id=None,
                pr_mensagem="MOCK: integracao HRBA simulada com sucesso",
            )
            return "sent"

        if not ORACLE_SEDE_DSN:
            raise ValueError("ORACLE_DSN (SEDE) nao configurado")

        sede = OracleSession(ORACLE_SEDE_DSN, nome="SEDE")
        hrba = OracleSession(get_hrba_dsn(), nome="HRBA")
        sede.connect()
        hrba.connect()

        nota = carregar_nota_sede(sede, nr_sequencia)
        if nota is None:
            raise ValueError(f"Nota nr_sequencia={nr_sequencia} nao encontrada na SEDE")

        ok_val, erro_tipo = validar_nota(hrba, nota)
        if not ok_val:
            msg = (
                "CNPJ emitente nao cadastrado no HRBA"
                if erro_tipo == "sem_fornecedor"
                else "Itens sem de-para de material no HRBA (cd_sistema_ant)"
            )
            upsert_processing_status(
                db,
                estabelecimento=ESTABELECIMENTO_NOME,
                nf=str(nota.get("NF") or meta["nf"] or nr_sequencia),
                status="dead_letter",
                tentativas=tentativas,
                erro=msg,
                erro_tipo=erro_tipo,
                nr_sequencia=nr_sequencia,
                fornecedor=str(nota.get("FORNECEDOR") or meta["fornecedor"] or ""),
                data_nf=nota.get("DATANOTA") or meta["data_nf"],
            )
            return "dead_letter"

        resultado = integrar_nota(sede, hrba, nota)
        nf = str(nota.get("NF") or meta["nf"] or nr_sequencia)
        fornecedor = str(nota.get("FORNECEDOR") or meta["fornecedor"] or "")
        data_nf = nota.get("DATANOTA") or meta["data_nf"]
        nr_seq_hrba = resultado.get("nr_seq_hrba")
        pr_id = int(nr_seq_hrba) if nr_seq_hrba is not None else None

        if resultado.get("ok"):
            status = "sent_existente" if resultado.get("ja_existia") else "sent"
            upsert_processing_status(
                db,
                estabelecimento=ESTABELECIMENTO_NOME,
                nf=nf,
                status=status,
                tentativas=tentativas,
                nr_sequencia=nr_sequencia,
                fornecedor=fornecedor,
                data_nf=data_nf,
                pr_id=pr_id,
                pr_mensagem=resultado.get("mensagem"),
            )
            return status

        upsert_processing_status(
            db,
            estabelecimento=ESTABELECIMENTO_NOME,
            nf=nf,
            status="retry_pending",
            tentativas=tentativas,
            erro=resultado.get("mensagem"),
            erro_tipo=resultado.get("erro_tipo") or "outro",
            nr_sequencia=nr_sequencia,
            fornecedor=fornecedor,
            data_nf=data_nf,
            pr_id=pr_id,
            pr_mensagem=resultado.get("mensagem"),
        )
        return "retry_pending"
    finally:
        if hrba is not None:
            hrba.close()
        if sede is not None:
            sede.close()
        db.close()
