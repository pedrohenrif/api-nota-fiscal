from __future__ import annotations

import logging
from typing import Any

from services.hrba_processor import queries
from services.hrba_processor.config import (
    CD_ESTABELECIMENTO_HRBA,
    CD_ESTOQUE_DIRETO,
    CENTRO_CUSTO_CONSIGNADO,
    CENTRO_CUSTO_ESTOQUE_DIRETO,
)
from services.hrba_processor.oracle_session import OracleSession

logger = logging.getLogger(__name__)

DEPARA_ESTOQUE = {
    54: 11,
    55: 71,
    56: 77,
    60: 1,
    61: 12,
    62: 15,
    63: 16,
    64: 21,
    65: 23,
    66: 57,
    67: 82,
    68: 26,
    69: 22,
    70: 31,
    97: 10,
}


def depara_estoque(cd_local_estoque: Any) -> int | None:
    try:
        key = int(cd_local_estoque)
    except (TypeError, ValueError):
        return None
    return DEPARA_ESTOQUE.get(key)


def depara_material(hrba: OracleSession, cd_sistema_anterior: Any) -> Any:
    rows = hrba.fetch_all(
        queries.SELECT_MATERIAL,
        {"CD_SISTEMA_ANT": str(cd_sistema_anterior)},
    )
    if not rows:
        return None
    return next(iter(rows[0].values()))


def buscar_unidades_medidas(hrba: OracleSession, cd_material: Any) -> tuple[Any, Any]:
    rows = hrba.fetch_all(queries.SELECT_UNIDADES_MEDIDAS, {"CD_MATERIAL": cd_material})
    if not rows:
        return None, None
    row = rows[0]
    return row.get("CD_UNIDADE_MEDIDA_COMPRA"), row.get("CD_UNIDADE_MEDIDA_ESTOQUE")


def _conta_valida(value: Any) -> bool:
    return value is not None and str(value).strip() not in ("", "None")


def conta_contabil_existe_hrba(hrba: OracleSession, cd_conta_contabil: Any) -> bool:
    """Garante que a conta existe no HRBA (evita ORA-02291 NOTFIIT_CONCONT_FK)."""
    if not _conta_valida(cd_conta_contabil):
        return False
    try:
        rows = hrba.fetch_all(
            queries.SELECT_CONTA_CONTABIL_EXISTE,
            {"CD_CONTA_CONTABIL": cd_conta_contabil},
        )
    except Exception:
        logger.warning(
            "Falha ao validar conta_contabil no HRBA | conta=%s",
            cd_conta_contabil,
            exc_info=True,
        )
        return False
    return bool(rows)


def buscar_conta_contabil(
    hrba: OracleSession,
    cd_material_hrba: Any,
    cd_local_estoque: Any = None,
) -> Any:
    """Busca conta contabil do material no HRBA (funcao Tasy + material_estab)."""
    params: dict[str, Any] = {
        "CD_ESTABELECIMENTO": CD_ESTABELECIMENTO_HRBA,
        "CD_MATERIAL": cd_material_hrba,
    }
    queries_try: list[tuple[str, dict[str, Any]]] = []
    # 2 args primeiro: em prod HRBA a assinatura com estoque pode nao existir (PLS-306).
    queries_try.append((queries.SELECT_CONTA_CONTABIL, params))
    if cd_local_estoque is not None:
        queries_try.append(
            (
                queries.SELECT_CONTA_CONTABIL_COM_ESTOQUE,
                {**params, "CD_LOCAL_ESTOQUE": cd_local_estoque},
            )
        )
    queries_try.append((queries.SELECT_CONTA_CONTABIL_MATERIAL_ESTAB, params))

    for sql, sql_params in queries_try:
        try:
            rows = hrba.fetch_all(sql, sql_params)
        except Exception:
            logger.warning(
                "Falha ao consultar conta contabil | material=%s local=%s",
                cd_material_hrba,
                cd_local_estoque,
                exc_info=True,
            )
            continue
        if not rows:
            continue
        value = next(iter(rows[0].values()))
        if not _conta_valida(value):
            continue
        if conta_contabil_existe_hrba(hrba, value):
            return value
        logger.warning(
            "Conta %s retornada para material %s nao existe em conta_contabil (HRBA)",
            value,
            cd_material_hrba,
        )
    return None


def resolver_conta_contabil(
    hrba: OracleSession, cd_material_hrba: Any, item: dict[str, Any]
) -> Any:
    """
    Conta contabil para o item HRBA:
    1) funcao/cadastro no HRBA (material_estab / obter_conta_contabil_material)
    2) CD_CONTA_CONTABIL do item SEDE, se existir no plano de contas do HRBA

    Nao usa CD_CONTA da SEDE como CD_CONTA_CONTABIL — costuma ser classe/grupo
    e estoura ORA-02291 (NOTFIIT_CONCONT_FK).
    """
    local_hrba = depara_estoque(item.get("CD_LOCAL_ESTOQUE"))
    conta = buscar_conta_contabil(hrba, cd_material_hrba, local_hrba)
    if conta is not None:
        return conta

    raw = item.get("CD_CONTA_CONTABIL")
    if _conta_valida(raw) and conta_contabil_existe_hrba(hrba, raw):
        logger.info(
            "Conta contabil via fallback item SEDE | material_hrba=%s valor=%s",
            cd_material_hrba,
            raw,
        )
        return raw
    if _conta_valida(raw):
        logger.warning(
            "CD_CONTA_CONTABIL SEDE=%s nao existe no plano de contas HRBA | material=%s",
            raw,
            cd_material_hrba,
        )
    return None


def verificar_cgc_emitente(hrba: OracleSession, cd_cgc: Any) -> bool:
    digits = "".join(ch for ch in str(cd_cgc or "") if ch.isdigit())
    rows = hrba.fetch_all(queries.SELECT_CGC_EMITENTE, {"cd_cgc": digits or cd_cgc})
    return bool(rows)


def atendimento_existe_hrba(hrba: OracleSession, nr_atendimento: Any) -> bool:
    if nr_atendimento is None or str(nr_atendimento).strip() in ("", "None", "0"):
        return False
    rows = hrba.fetch_all(
        queries.SELECT_ATENDIMENTO_EXISTE,
        {"nr_atendimento": nr_atendimento},
    )
    return bool(rows)


def nr_atendimento_do_item(item: dict[str, Any]) -> Any:
    raw = item.get("NR_ATENDIMENTO") or item.get("NR_DOC_IMPORTACAO")
    if raw is None or str(raw).strip() in ("", "None", "0"):
        return None
    return raw


def definir_centro_custo(cd_estoque_hrba: Any, consignado: str) -> int | None:
    if cd_estoque_hrba == CD_ESTOQUE_DIRETO:
        return CENTRO_CUSTO_ESTOQUE_DIRETO
    if consignado == "S":
        return CENTRO_CUSTO_CONSIGNADO
    return None


def validar_nota(hrba: OracleSession, nota: dict[str, Any]) -> tuple[bool, str | None]:
    """Retorna (ok, erro_tipo)."""
    fornecedor = nota.get("FORNECEDOR")
    if not verificar_cgc_emitente(hrba, fornecedor):
        return False, "sem_fornecedor"

    faltando: list[str] = []
    estoques_sem_depara: list[str] = []
    atendimentos_inexistentes: list[str] = []
    cache_atend: dict[str, bool] = {}

    for item in nota.get("NOTA_FISCAL_ITEM") or []:
        material_sede = str(item.get("CD_MATERIAL") or "")
        if not material_sede:
            faltando.append("(sem codigo)")
            continue
        if depara_material(hrba, material_sede) is None:
            ds = item.get("DS_REDUZIDA") or ""
            faltando.append(f"{material_sede} {ds}".strip())
            nota.setdefault("ITENS_SEM_DEPARA", []).append(
                [item.get("CD_MATERIAL"), item.get("DS_REDUZIDA")]
            )
        local = item.get("CD_LOCAL_ESTOQUE")
        if depara_estoque(local) is None:
            chave = str(local)
            if chave not in estoques_sem_depara:
                estoques_sem_depara.append(chave)

        # Opcao B: so valida quando a SEDE trouxe atendimento preenchido.
        nr_atend = nr_atendimento_do_item(item)
        if nr_atend is not None:
            chave_atend = str(nr_atend).strip()
            if chave_atend not in cache_atend:
                cache_atend[chave_atend] = atendimento_existe_hrba(hrba, nr_atend)
            if not cache_atend[chave_atend] and chave_atend not in atendimentos_inexistentes:
                atendimentos_inexistentes.append(chave_atend)

    if faltando:
        logger.warning("HRBA sem de-para material: %s", ", ".join(faltando[:10]))
        return False, "sem_depara"
    if estoques_sem_depara:
        nota["ESTOQUES_SEM_DEPARA"] = estoques_sem_depara
        logger.warning(
            "HRBA sem de-para estoque (SEDE->HRBA): %s",
            ", ".join(estoques_sem_depara),
        )
        return False, "sem_depara_estoque"
    if atendimentos_inexistentes:
        nota["ATENDIMENTOS_INEXISTENTES"] = atendimentos_inexistentes
        logger.warning(
            "HRBA atendimento inexistente: %s",
            ", ".join(atendimentos_inexistentes),
        )
        return False, "atendimento_inexistente"
    return True, None
