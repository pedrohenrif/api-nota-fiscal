from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from services.extractor.extraction_profiles import ExtractionProfile


@dataclass(frozen=True)
class NoteValidationResult:
    valido: bool
    mensagem: str | None = None
    cd_operacao_nf: int | None = None
    operacoes_liberadas: tuple[int, ...] = ()


def _g(row: dict[str, Any], key: str, default: Any = None) -> Any:
    return row.get(key, row.get(key.upper(), row.get(key.lower(), default)))


def _as_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return None


def validate_note_row(
    note_row: dict[str, Any], profile: ExtractionProfile
) -> NoteValidationResult:
    operacoes = profile.cd_operacao_nf_in
    cd_operacao = _g(note_row, "CD_OPERACAO_NF")
    cd_operacao_int = int(cd_operacao) if cd_operacao is not None else None

    if _g(note_row, "IE_TIPO_NOTA") and _g(note_row, "IE_TIPO_NOTA") != "EN":
        return NoteValidationResult(
            valido=False,
            mensagem="Nota com tipo diferente de entrada (EN).",
            cd_operacao_nf=cd_operacao_int,
            operacoes_liberadas=operacoes,
        )

    if _g(note_row, "DT_INTEGRACAO") is not None:
        return NoteValidationResult(
            valido=False,
            mensagem="Nota ja integrada no Tasy (dt_integracao preenchida).",
            cd_operacao_nf=cd_operacao_int,
            operacoes_liberadas=operacoes,
        )

    ie_situacao = _g(note_row, "IE_SITUACAO")
    if ie_situacao in (2, 3):
        return NoteValidationResult(
            valido=False,
            mensagem=f"Nota com situacao invalida (ie_situacao={ie_situacao}).",
            cd_operacao_nf=cd_operacao_int,
            operacoes_liberadas=operacoes,
        )

    cd_estab = _g(note_row, "CD_ESTABELECIMENTO")
    if cd_estab is not None and int(cd_estab) != profile.cd_estabelecimento:
        return NoteValidationResult(
            valido=False,
            mensagem=(
                f"Nota pertence ao estabelecimento {cd_estab}, "
                f"esperado {profile.cd_estabelecimento}."
            ),
            cd_operacao_nf=cd_operacao_int,
            operacoes_liberadas=operacoes,
        )

    if cd_operacao_int is not None and cd_operacao_int not in operacoes:
        liberadas = ", ".join(str(op) for op in operacoes)
        return NoteValidationResult(
            valido=False,
            mensagem=(
                f"Esta nota possui operacao {cd_operacao_int}, diferente das "
                f"liberadas ({liberadas})."
            ),
            cd_operacao_nf=cd_operacao_int,
            operacoes_liberadas=operacoes,
        )

    dt_emissao = _as_date(_g(note_row, "DATANOTA"))
    dt_emissao_min = date.fromisoformat(profile.dt_emissao_min)
    if dt_emissao and dt_emissao < dt_emissao_min:
        return NoteValidationResult(
            valido=False,
            mensagem=(
                f"Data de emissao anterior ao minimo permitido "
                f"({profile.dt_emissao_min})."
            ),
            cd_operacao_nf=cd_operacao_int,
            operacoes_liberadas=operacoes,
        )

    dt_estoque = _as_date(_g(note_row, "DT_ATUALIZACAO_ESTOQUE"))
    dt_estoque_min = date.fromisoformat(profile.dt_atualizacao_estoque_min)
    if dt_estoque and dt_estoque < dt_estoque_min:
        return NoteValidationResult(
            valido=False,
            mensagem=(
                f"Data de atualizacao de estoque anterior ao minimo permitido "
                f"({profile.dt_atualizacao_estoque_min})."
            ),
            cd_operacao_nf=cd_operacao_int,
            operacoes_liberadas=operacoes,
        )

    return NoteValidationResult(
        valido=True,
        cd_operacao_nf=cd_operacao_int,
        operacoes_liberadas=operacoes,
    )
