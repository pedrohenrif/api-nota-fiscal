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


def buscar_conta_contabil(hrba: OracleSession, cd_material_hrba: Any) -> Any:
    """Igual GA0016: obter_conta_contabil_material(1, cd_material) no MATERIAL HRBA."""
    try:
        rows = hrba.fetch_all(
            queries.SELECT_CONTA_CONTABIL,
            {"CD_MATERIAL": cd_material_hrba},
        )
    except Exception:
        logger.warning(
            "Falha ao consultar conta contabil | material=%s",
            cd_material_hrba,
            exc_info=True,
        )
        return None
    if not rows:
        return None
    return next(iter(rows[0].values()))


def resolver_conta_contabil(
    hrba: OracleSession, cd_material_hrba: Any, item: dict[str, Any]
) -> Any:
    """
    Conta contabil alinhada ao GA0016:
    so obter_conta_contabil_material(1, material_hrba).

    Nao usa CD_CONTA_CONTABIL da SEDE: em prod a conta da SEDE muitas vezes
    nao existe no plano do HRBA e estoura ORA-02291 (NOTFIIT_CONCONT_FK).
    """
    conta = buscar_conta_contabil(hrba, cd_material_hrba)
    if _conta_valida(conta):
        return conta
    sede_conta = item.get("CD_CONTA_CONTABIL")
    if _conta_valida(sede_conta):
        logger.warning(
            "Funcao conta NULL no HRBA; ignorando CD_CONTA_CONTABIL SEDE=%s "
            "(evita ORA-02291) | material_hrba=%s",
            sede_conta,
            cd_material_hrba,
        )
    # GA0016: INSERT com null quando a funcao nao retorna conta.
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
    """Retorna (ok, erro_tipo).

    Valida de-para e conta contábil ANTES de qualquer INSERT no HRBA, para nao
    deixar nota parcial no Tasy quando o cadastro do material esta incompleto.
    """
    fornecedor = nota.get("FORNECEDOR")
    if not verificar_cgc_emitente(hrba, fornecedor):
        return False, "sem_fornecedor"

    faltando: list[str] = []
    estoques_sem_depara: list[str] = []
    sem_conta: list[str] = []
    atendimentos_inexistentes: list[str] = []
    cache_atend: dict[str, bool] = {}
    cache_conta: dict[str, Any] = {}

    for item in nota.get("NOTA_FISCAL_ITEM") or []:
        material_sede = str(item.get("CD_MATERIAL") or "")
        if not material_sede:
            faltando.append("(sem codigo)")
            continue
        cd_material_hrba = depara_material(hrba, material_sede)
        if cd_material_hrba is None:
            ds = item.get("DS_REDUZIDA") or ""
            faltando.append(f"{material_sede} {ds}".strip())
            nota.setdefault("ITENS_SEM_DEPARA", []).append(
                [item.get("CD_MATERIAL"), item.get("DS_REDUZIDA")]
            )
        else:
            chave_mat = str(cd_material_hrba)
            if chave_mat not in cache_conta:
                cache_conta[chave_mat] = buscar_conta_contabil(hrba, cd_material_hrba)
            if not _conta_valida(cache_conta[chave_mat]):
                ds = item.get("DS_REDUZIDA") or ""
                sem_conta.append(
                    f"sede={material_sede}->hrba={cd_material_hrba} {ds}".strip()
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
    if sem_conta:
        # Unicos preservando ordem
        vistos: set[str] = set()
        unicos: list[str] = []
        for item in sem_conta:
            if item not in vistos:
                vistos.add(item)
                unicos.append(item)
        nota["MATERIAIS_SEM_CONTA"] = unicos
        logger.warning(
            "HRBA material sem conta contabil (obter_conta_contabil_material): %s",
            "; ".join(unicos[:10]),
        )
        return False, "conta_contabil"
    if atendimentos_inexistentes:
        nota["ATENDIMENTOS_INEXISTENTES"] = atendimentos_inexistentes
        logger.warning(
            "HRBA atendimento inexistente: %s",
            ", ".join(atendimentos_inexistentes),
        )
        return False, "atendimento_inexistente"
    return True, None
