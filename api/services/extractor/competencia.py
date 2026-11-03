"""Janela de competencia / piso de datas para extracao."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Any

from services.extractor.config import COMPETENCIA_MES_ATUAL_ONLY

if TYPE_CHECKING:
    from services.extractor.extraction_profiles import ExtractionProfile


def _primeiro_dia_mes(ano: int, mes: int) -> date:
    return date(ano, mes, 1)


def _mes_anterior(ref: date) -> date:
    if ref.month == 1:
        return date(ref.year - 1, 12, 1)
    return date(ref.year, ref.month - 1, 1)


def resolve_extraction_date_params(
    profile: ExtractionProfile, hoje: date | None = None
) -> dict[str, Any]:
    """
    Monta binds de data/competencia para o SQL de cabecalho.

    HRBA (competencia_mes_anterior_ate_dia=5):
      - dias 1..5: piso = 1o dia do mes anterior; aceita mes atual e anterior
      - a partir do dia 6: piso = 1o dia do mes atual; so competencia atual
    Demais unidades: usa dt_* do profile + COMPETENCIA_MES_ATUAL_ONLY.
    """
    hoje = hoje or date.today()
    grace = int(getattr(profile, "competencia_mes_anterior_ate_dia", 0) or 0)

    if grace > 0:
        if hoje.day <= grace:
            piso = _mes_anterior(hoje)
        else:
            piso = _primeiro_dia_mes(hoje.year, hoje.month)
        # Nao passa do piso absoluto do profile (se configurado mais restritivo).
        piso_abs = date.fromisoformat(profile.dt_emissao_min)
        if piso < piso_abs:
            piso = piso_abs
        estoque_piso = piso
        estoque_abs = date.fromisoformat(profile.dt_atualizacao_estoque_min)
        if estoque_piso < estoque_abs:
            estoque_piso = estoque_abs
        return {
            "dt_emissao_min": piso.isoformat(),
            "dt_atualizacao_estoque_min": estoque_piso.isoformat(),
            "competencia_mes_atual": 1,
            "competencia_grace_ate_dia": grace,
        }

    return {
        "dt_emissao_min": profile.dt_emissao_min,
        "dt_atualizacao_estoque_min": profile.dt_atualizacao_estoque_min,
        "competencia_mes_atual": 1 if COMPETENCIA_MES_ATUAL_ONLY else 0,
        "competencia_grace_ate_dia": 0,
    }


def emissao_na_competencia_permitida(
    dt_emissao: date,
    profile: ExtractionProfile,
    hoje: date | None = None,
) -> tuple[bool, str]:
    """Valida competencia (mes atual + mes anterior ate o dia de corte no HRBA)."""
    hoje = hoje or date.today()
    grace = int(getattr(profile, "competencia_mes_anterior_ate_dia", 0) or 0)

    if grace > 0:
        mes_atual = (hoje.year, hoje.month)
        mes_nota = (dt_emissao.year, dt_emissao.month)
        if mes_nota == mes_atual:
            return True, ""
        if hoje.day <= grace:
            ant = _mes_anterior(hoje)
            if mes_nota == (ant.year, ant.month):
                return True, ""
            return False, (
                f"Nota fora da janela HRBA (emissao {dt_emissao.isoformat()}; "
                f"ate o dia {grace} aceita {ant.year:04d}-{ant.month:02d} e "
                f"{hoje.year:04d}-{hoje.month:02d})."
            )
        return False, (
            f"Nota fora da competencia do mes atual "
            f"(emissao {dt_emissao.isoformat()}; esperado "
            f"{hoje.year:04d}-{hoje.month:02d}; "
            f"mes anterior so ate o dia {grace})."
        )

    if not COMPETENCIA_MES_ATUAL_ONLY:
        return True, ""

    if dt_emissao.year == hoje.year and dt_emissao.month == hoje.month:
        return True, ""
    return False, (
        f"Nota fora da competencia do mes atual "
        f"(emissao {dt_emissao.isoformat()}; esperado "
        f"{hoje.year:04d}-{hoje.month:02d})."
    )
