from __future__ import annotations

import logging
from typing import Any

from services.hrba_processor import queries
from services.hrba_processor.config import (
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


def buscar_conta_contabil(hrba: OracleSession, cd_material_hrba: Any) -> Any:
    rows = hrba.fetch_all(queries.SELECT_CONTA_CONTABIL, {"CD_MATERIAL": cd_material_hrba})
    if not rows:
        return None
    return next(iter(rows[0].values()))


def verificar_cgc_emitente(hrba: OracleSession, cd_cgc: Any) -> bool:
    digits = "".join(ch for ch in str(cd_cgc or "") if ch.isdigit())
    rows = hrba.fetch_all(queries.SELECT_CGC_EMITENTE, {"cd_cgc": digits or cd_cgc})
    return bool(rows)


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

    if faltando:
        logger.warning("HRBA sem de-para: %s", ", ".join(faltando[:10]))
        return False, "sem_depara"
    return True, None
