from __future__ import annotations

import logging
from typing import Any

from services.hrba_processor import queries
from services.hrba_processor.config import (
    CD_ESTABELECIMENTO_HRBA,
    CD_MATERIAL_ESTOQUE,
    CD_NATUREZA_OPERACAO,
    USUARIO_INTEGRACAO,
)
from services.hrba_processor.depara import (
    buscar_conta_contabil,
    buscar_unidades_medidas,
    definir_centro_custo,
    depara_estoque,
    depara_material,
)
from services.hrba_processor.oracle_session import OracleSession

logger = logging.getLogger(__name__)


def _ident(nota: dict[str, Any], nr_seq_hrba: Any = None) -> str:
    base = f"NF={nota.get('NF')} seq_sede={nota.get('NR_SEQUENCIA')}"
    if nr_seq_hrba is not None:
        return f"{base} seq_hrba={nr_seq_hrba}"
    return base


def _lookup_nr_seq_hrba(hrba: OracleSession, nota: dict[str, Any]) -> Any:
    return hrba.fetch_value(
        queries.SELECT_NR_SEQ_HRBA,
        {
            "NR_NOTA_FISCAL": nota.get("NF"),
            "CD_CGC_EMITENTE": nota.get("FORNECEDOR"),
            "CD_ESTABELECIMENTO": CD_ESTABELECIMENTO_HRBA,
            "CD_SERIE_NF": nota.get("SERIE"),
            "NR_SEQUENCIA_NF": nota.get("NR_SEQUENCIA_NF"),
        },
    )


def _inserir_nota_fiscal(hrba: OracleSession, nota: dict[str, Any]) -> bool:
    try:
        hrba.execute(
            queries.INSERT_NF,
            {
                "FORNECEDOR": nota.get("FORNECEDOR"),
                "DATANOTA": nota.get("DATANOTA"),
                "ATUALIZACAO": nota.get("ATUALIZACAO"),
                "SERIE": nota.get("SERIE"),
                "DATAREC": nota.get("DATAREC"),
                "DESCONTO": nota.get("DESCONTO") or 0,
                "IPI": nota.get("IPI") or 0,
                "FRETE": nota.get("FRETE") or 0,
                "NF": nota.get("NF"),
                "ESTABELECIMENTO": CD_ESTABELECIMENTO_HRBA,
                "VALOR_TOTAL_NOTA": nota.get("VALOR_TOTAL_NOTA"),
                "PESO_LIQUIDO": nota.get("PESO_LIQUIDO"),
                "QT_PESO_BRUTO": nota.get("QT_PESO_BRUTO"),
                "USUARIO": USUARIO_INTEGRACAO,
                "NR_SEQUENCIA_NF": nota.get("NR_SEQUENCIA_NF"),
                "CNPJ": nota.get("CNPJ"),
                "OPERACAO": nota.get("OPERACAO"),
                "ACAO_NF": nota.get("ACAO_NF"),
                "IE_EMISSAO_NF": nota.get("EMISSAO_NF"),
                "TIPO_FRETE": nota.get("TIPO_FRETE"),
                "VL_MERCADORIA": nota.get("VL_MERCADORIA"),
                "DS_OBSERVACAO": nota.get("DS_OBSERVACAO"),
            },
        )
        return True
    except Exception:
        logger.exception("[INSERT_NF] falha | %s", _ident(nota))
        return False


def _inserir_itens(hrba: OracleSession, nota: dict[str, Any], nr_seq_hrba: Any) -> bool:
    ok = True
    consignado = str(nota.get("CONSIGNADO") or "N")
    for item in nota.get("NOTA_FISCAL_ITEM") or []:
        material_sede = str(item.get("CD_MATERIAL") or "")
        cd_material_hrba = depara_material(hrba, material_sede)
        cd_estoque_hrba = depara_estoque(item.get("CD_LOCAL_ESTOQUE"))
        if cd_material_hrba is None or cd_estoque_hrba is None:
            ok = False
            logger.error(
                "[INSERT_NFI] de-para incompleto | %s | material=%s estoque=%s",
                _ident(nota, nr_seq_hrba),
                material_sede,
                item.get("CD_LOCAL_ESTOQUE"),
            )
            continue

        un_compra, un_estoque = buscar_unidades_medidas(hrba, cd_material_hrba)
        conta = buscar_conta_contabil(hrba, cd_material_hrba)
        centro = definir_centro_custo(cd_estoque_hrba, consignado)

        try:
            hrba.execute(
                queries.INSERT_NFI,
                {
                    "NR_SEQUENCIA": nr_seq_hrba,
                    "CD_ESTABELECIMENTO": CD_ESTABELECIMENTO_HRBA,
                    "CD_SERIE_NF": item.get("CD_SERIE_NF"),
                    "NR_SEQUENCIA_NF": item.get("NR_SEQUENCIA_NF"),
                    "NR_ITEM_NF": item.get("NR_ITEM_NF"),
                    "QT_ITEM_NF": item.get("QT_ITEM_NF"),
                    "VL_UNITARIO_ITEM_NF": item.get("VL_UNITARIO_ITEM_NF"),
                    "VL_TOTAL_ITEM_NF": item.get("VL_TOTAL_ITEM_NF"),
                    "DT_ATUALIZACAO": item.get("DT_ATUALIZACAO"),
                    "NM_USUARIO": USUARIO_INTEGRACAO,
                    "VL_FRETE": item.get("VL_FRETE") or 0,
                    "VL_DESCONTO": item.get("VL_DESCONTO") or 0,
                    "VL_DESPESA_ACESSORIA": item.get("VL_DESPESA_ACESSORIA") or 0,
                    "VL_DESCONTO_RATEIO": item.get("VL_DESCONTO_RATEIO") or 0,
                    "VL_SEGURO": item.get("VL_SEGURO") or 0,
                    "VL_LIQUIDO": item.get("VL_LIQUIDO"),
                    "NR_NOTA_FISCAL": item.get("NR_NOTA_FISCAL"),
                    "CD_MATERIAL": cd_material_hrba,
                    "CD_CONTA_CONTABIL": conta,
                    "CD_UNIDADE_MEDIDA_COMPRA": un_compra,
                    "CD_UNIDADE_MEDIDA_ESTOQUE": un_estoque,
                    "NR_SEQ_ITEM_LOTE": item.get("NR_SEQ_ITEM_LOTE"),
                    "CD_LOTE_FABRICACAO": item.get("CD_LOTE_FABRICACAO"),
                    "CD_LOCAL_ESTOQUE": cd_estoque_hrba,
                    "DT_VALIDADE": item.get("DT_VALIDADE"),
                    "CD_NATUREZA_OPERACAO": CD_NATUREZA_OPERACAO,
                    "CD_CGC_EMITENTE": item.get("CD_CGC_EMITENTE"),
                    "CD_PROCEDIMENTO": item.get("CD_PROCEDIMENTO"),
                    "IE_ORIGEM_PROCED": item.get("IE_ORIGEM_PROCED"),
                    "CD_SEQUENCIA_PARAMETRO": item.get("CD_SEQUENCIA_PARAMETRO"),
                    "CD_CATEGORIA_IVA": item.get("CD_CATEGORIA_IVA"),
                    "CD_PROCEDIMENTO_LOC": item.get("CD_PROCEDIMENTO_LOC"),
                    "DT_ATUALIZACAO_ESTOQUE": item.get("DT_ATUALIZACAO_ESTOQUE"),
                    "QT_ITEM_ESTOQUE": item.get("QT_ITEM_ESTOQUE"),
                    "CENTRO_CUSTO": centro,
                    "CD_MATERIAL_ESTOQUE": CD_MATERIAL_ESTOQUE,
                },
            )
        except Exception:
            ok = False
            logger.exception(
                "[INSERT_NFI] falha item=%s | %s",
                item.get("NR_ITEM_NF"),
                _ident(nota, nr_seq_hrba),
            )
    return ok


def _inserir_lotes(hrba: OracleSession, nota: dict[str, Any], nr_seq_hrba: Any) -> bool:
    try:
        for lote in nota.get("NOTA_FISCAL_ITEM_LOTE") or []:
            existente = hrba.fetch_all(
                queries.SELECT_LOTE_FORNEC_EXIST,
                {"NR_SEQUENCIA": nr_seq_hrba, "NR_ITEM_NF": lote.get("NR_ITEM_NF")},
            )
            if existente and any(next(iter(r.values())) is not None for r in existente):
                continue
            hrba.execute(
                queries.INSERT_NFIL,
                {
                    "NM_USUARIO": USUARIO_INTEGRACAO,
                    "NR_SEQUENCIA": nr_seq_hrba,
                    "NR_ITEM_NF": lote.get("NR_ITEM_NF"),
                    "DT_VALIDADE_LOTE": lote.get("DT_VALIDADE"),
                    "QT_MATERIAL_LOTE": lote.get("QT_MATERIAL"),
                    "DS_LOTE_FORNECEDOR": lote.get("CD_LOTE_FABRICACAO"),
                    "IE_INDETERMINADA": lote.get("IE_INDETERMINADO"),
                    "CD_BARRA_MATERIAL": lote.get("CD_BARRA_MATERIAL"),
                    "DS_BARRAS": lote.get("DS_BARRAS"),
                },
            )
        return True
    except Exception:
        logger.exception("[INSERT_NFIL] falha | %s", _ident(nota, nr_seq_hrba))
        return False


def _inserir_vencimentos(hrba: OracleSession, nota: dict[str, Any], nr_seq_hrba: Any) -> bool:
    try:
        for venc in nota.get("NOTA_FISCAL_VENC") or []:
            hrba.execute(
                queries.INSERT_NFV,
                {
                    "NR_SEQUENCIA": nr_seq_hrba,
                    "CD_ESTABELECIMENTO": CD_ESTABELECIMENTO_HRBA,
                    "CD_SERIE_NF": venc.get("CD_SERIE_NF"),
                    "NR_SEQUENCIA_NF": venc.get("NR_SEQUENCIA_NF"),
                    "DT_VENCIMENTO": venc.get("DT_VENCIMENTO"),
                    "VL_VENCIMENTO": venc.get("VL_VENCIMENTO"),
                    "DT_ATUALIZACAO": venc.get("DT_ATUALIZACAO"),
                    "NM_USUARIO": USUARIO_INTEGRACAO,
                    "NR_NOTA_FISCAL": venc.get("NR_NOTA_FISCAL"),
                    "IE_ORIGEM": venc.get("IE_ORIGEM"),
                    "CD_CGC_EMITENTE": venc.get("CD_CGC_EMITENTE"),
                },
            )
        return True
    except Exception:
        logger.exception("[INSERT_NFV] falha | %s", _ident(nota, nr_seq_hrba))
        return False


def _consignado(
    sede: OracleSession,
    hrba: OracleSession,
    nota: dict[str, Any],
    nr_seq_hrba: Any,
) -> bool:
    if str(nota.get("CONSIGNADO") or "N") != "S":
        return True
    try:
        atendimentos = sede.fetch_all(
            queries.SELECT_NR_ATENDIMENTO,
            {"nr_sequencia": nota.get("NR_SEQUENCIA")},
        )
        if not atendimentos:
            logger.warning("[CONSIGNADO] sem atendimento | %s", _ident(nota, nr_seq_hrba))
            return True
        nr_atendimento = atendimentos[0].get("NR_ATENDIMENTO")
        dt_atendimento = atendimentos[0].get("DT_ATENDIMENTO")
        for item in nota.get("NOTA_FISCAL_ITEM") or []:
            hrba.callproc(
                "gravar_atend_lancar_nf",
                [
                    nr_seq_hrba,
                    item.get("NR_ITEM_NF"),
                    nr_atendimento,
                    dt_atendimento,
                    USUARIO_INTEGRACAO,
                ],
            )
            hrba.commit()
        return True
    except Exception as exc:
        logger.exception("[CONSIGNADO] falha | %s", _ident(nota, nr_seq_hrba))
        nota.setdefault("INCONSISTENCIA_PROCEDURE", []).append(str(exc))
        return False


def _executar_procedures(hrba: OracleSession, nota: dict[str, Any], nr_seq_hrba: Any) -> bool:
    inconsistencias: list[str] = nota.setdefault("INCONSISTENCIA_PROCEDURE", [])
    nota_valida = True
    ds_erro_item = None
    ds_erro_nota = None
    consistir_ok = False
    conn = hrba.connection
    if conn is None:
        inconsistencias.append("conexao HRBA indisponivel para procedures")
        return False

    try:
        with conn.cursor() as cursor:
            ds_erro_item_var = cursor.var(str)
            ds_erro_nota_var = cursor.var(str)
            cursor.callproc(
                "consistir_nota_fiscal",
                [nr_seq_hrba, USUARIO_INTEGRACAO, ds_erro_item_var, ds_erro_nota_var, "S", "N"],
            )
            hrba.commit()
            consistir_ok = True
            ds_erro_item = ds_erro_item_var.getvalue()
            ds_erro_nota = ds_erro_nota_var.getvalue()
            if ds_erro_item:
                inconsistencias.append(str(ds_erro_item))
                nota_valida = False
            if ds_erro_nota:
                inconsistencias.append(str(ds_erro_nota))
                nota_valida = False
    except Exception as exc:
        logger.exception("[PROCEDURE] consistir_nf | %s", _ident(nota, nr_seq_hrba))
        inconsistencias.append(f"consistir_nf: {exc}")

    try:
        with conn.cursor() as cursor:
            ds_erro_var = cursor.var(str)
            cursor.callproc(
                "consiste_aprovacao_nota_fiscal",
                [nr_seq_hrba, USUARIO_INTEGRACAO, ds_erro_var],
            )
            hrba.commit()
            ds_erro = ds_erro_var.getvalue()
            if ds_erro:
                inconsistencias.append(str(ds_erro))
                nota_valida = False
    except Exception as exc:
        logger.exception("[PROCEDURE] aprovacao_nf | %s", _ident(nota, nr_seq_hrba))
        inconsistencias.append(f"aprovacao_nf: {exc}")

    try:
        hrba.callproc(
            "gerar_lote_fornec_nf",
            [nr_seq_hrba, "S", USUARIO_INTEGRACAO, "N", "S"],
        )
    except Exception as exc:
        logger.exception("[PROCEDURE] gerar_lote | %s", _ident(nota, nr_seq_hrba))
        inconsistencias.append(f"gerar_lote: {exc}")

    try:
        with conn.cursor() as cursor:
            ds_retorno_var = cursor.var(str)
            cursor.callproc(
                "gerar_divergencia_nota_ordem",
                [nr_seq_hrba, USUARIO_INTEGRACAO, ds_retorno_var],
            )
            hrba.commit()
            ds_retorno = ds_retorno_var.getvalue()
            if ds_retorno:
                inconsistencias.append(str(ds_retorno))
                nota_valida = False
    except Exception as exc:
        logger.exception("[PROCEDURE] divergencia | %s", _ident(nota, nr_seq_hrba))
        inconsistencias.append(f"divergencia: {exc}")

    if consistir_ok and not ds_erro_item and not ds_erro_nota:
        try:
            hrba.callproc(
                "atualizar_nota_fiscal",
                [nr_seq_hrba, "1", USUARIO_INTEGRACAO, 1, "S"],
            )
            hrba.commit()
        except Exception as exc:
            logger.exception("[PROCEDURE] atualizar_nf | %s", _ident(nota, nr_seq_hrba))
            inconsistencias.append(f"atualizar_nf: {exc}")
            nota_valida = False

    return nota_valida


def _confirmar_integracao(
    hrba: OracleSession,
    sede: OracleSession,
    nota: dict[str, Any],
    nr_seq_hrba: Any,
) -> bool:
    dt_estoque = hrba.fetch_value(
        queries.VALIDAR_INTEGRACAO,
        {"NR_SEQUENCIA": nr_seq_hrba},
    )
    if not dt_estoque:
        logger.warning(
            "[VALIDAR] estoque HRBA nao atualizado | %s", _ident(nota, nr_seq_hrba)
        )
        return False
    sede.execute(
        queries.UPDATE_DT_INTEGRACAO,
        {"nr_sequencia": nota.get("NR_SEQUENCIA")},
    )
    sede.commit()
    logger.info("[VALIDAR] SEDE dt_integracao OK | %s", _ident(nota, nr_seq_hrba))
    return True


def integrar_nota(
    sede: OracleSession,
    hrba: OracleSession,
    nota: dict[str, Any],
) -> dict[str, Any]:
    """
    Integra uma nota SEDE -> HRBA.
    Retorno: {ok, nr_seq_hrba, ja_existia, mensagem, erro_tipo}
    """
    existente = _lookup_nr_seq_hrba(hrba, nota)
    if existente:
        logger.info("[INTEGRACAO] NF ja existe no HRBA | %s", _ident(nota, existente))
        nr_seq_hrba = existente
        ja_existia = True
    else:
        ja_existia = False
        if not _inserir_nota_fiscal(hrba, nota):
            return {
                "ok": False,
                "nr_seq_hrba": None,
                "ja_existia": False,
                "mensagem": "Falha ao inserir NOTA_FISCAL no HRBA",
                "erro_tipo": "outro",
            }
        nr_seq_hrba = _lookup_nr_seq_hrba(hrba, nota)
        if nr_seq_hrba is None:
            return {
                "ok": False,
                "nr_seq_hrba": None,
                "ja_existia": False,
                "mensagem": "INSERT_NF sem nr_sequencia gerado no HRBA",
                "erro_tipo": "outro",
            }
        if not _inserir_itens(hrba, nota, nr_seq_hrba):
            hrba.rollback()
            return {
                "ok": False,
                "nr_seq_hrba": nr_seq_hrba,
                "ja_existia": False,
                "mensagem": "Falha ao inserir itens no HRBA",
                "erro_tipo": "sem_depara",
            }
        _inserir_lotes(hrba, nota, nr_seq_hrba)
        _inserir_vencimentos(hrba, nota, nr_seq_hrba)
        _consignado(sede, hrba, nota, nr_seq_hrba)

    _executar_procedures(hrba, nota, nr_seq_hrba)
    hrba.commit()

    integrada = _confirmar_integracao(hrba, sede, nota, nr_seq_hrba)
    inconsistencias = nota.get("INCONSISTENCIA_PROCEDURE") or []

    if integrada:
        return {
            "ok": True,
            "nr_seq_hrba": nr_seq_hrba,
            "ja_existia": ja_existia,
            "mensagem": (
                "Nota ja existia no HRBA; estoque confirmado e SEDE marcada."
                if ja_existia
                else "Nota integrada no HRBA e SEDE marcada (dt_integracao)."
            ),
            "erro_tipo": None,
        }

    msg = "; ".join(str(x) for x in inconsistencias if x) or (
        "Procedures executadas, mas dt_atualizacao_estoque no HRBA ficou vazia"
    )
    return {
        "ok": False,
        "nr_seq_hrba": nr_seq_hrba,
        "ja_existia": ja_existia,
        "mensagem": msg,
        "erro_tipo": "inconsistencia_tasy" if inconsistencias else "estoque_nao_atualizado",
    }
