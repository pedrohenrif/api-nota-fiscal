from dataclasses import dataclass
from datetime import date
from typing import Literal


# Data mínima inclusiva de dt_atualizacao_estoque (piso operacional).
DT_ATUALIZACAO_ESTOQUE_MIN = "2026-08-05"

DestinoIntegracao = Literal["pr", "hrba"]


@dataclass(frozen=True)
class ExtractionProfile:
    estabelecimento_nome: str
    cd_estabelecimento: int
    dt_emissao_min: str
    cd_operacao_nf_in: tuple[int, ...]
    cd_operacao_nf_item_not_in: tuple[int, ...]
    dt_atualizacao_estoque_min: str = DT_ATUALIZACAO_ESTOQUE_MIN
    # pr = fila nf.raw (processor PR); hrba = fila nf.hrba.raw (Tasy->Tasy)
    destino: DestinoIntegracao = "pr"


PROFILES = {
    "Castelo": ExtractionProfile(
        estabelecimento_nome="Castelo",
        cd_estabelecimento=8,
        dt_emissao_min="2024-05-14",
        cd_operacao_nf_in=(1, 39),
        cd_operacao_nf_item_not_in=(33,),
    ),
    "HRAS": ExtractionProfile(
        estabelecimento_nome="HRAS",
        cd_estabelecimento=9,
        dt_emissao_min="2024-05-14",
        cd_operacao_nf_in=(1, 39),
        cd_operacao_nf_item_not_in=(33,),
    ),
    # HRT — Itaituba
    "HRT": ExtractionProfile(
        estabelecimento_nome="HRT",
        cd_estabelecimento=7,
        dt_emissao_min="2024-05-14",
        cd_operacao_nf_in=(1, 39),
        cd_operacao_nf_item_not_in=(33,),
    ),
    "Ponta Pora": ExtractionProfile(
        estabelecimento_nome="Ponta Pora",
        cd_estabelecimento=16,
        dt_emissao_min="2024-05-14",
        cd_operacao_nf_in=(1, 39),
        cd_operacao_nf_item_not_in=(33,),
    ),
    # HRBA — SEDE estab 10 -> Tasy HRBA (nao PR)
    "HRBA": ExtractionProfile(
        estabelecimento_nome="HRBA",
        cd_estabelecimento=10,
        dt_emissao_min="2026-09-01",
        cd_operacao_nf_in=(1, 21, 22, 37, 39),
        cd_operacao_nf_item_not_in=(),
        destino="hrba",
    ),
}


def assert_estoque_min_parseable() -> None:
    date.fromisoformat(DT_ATUALIZACAO_ESTOQUE_MIN)


def queue_name_for_estabelecimento(estabelecimento: str) -> str:
    from services.extractor.config import RABBITMQ_QUEUE_HRBA_RAW, RABBITMQ_QUEUE_RAW_NF

    profile = PROFILES.get(estabelecimento)
    if profile is not None and profile.destino == "hrba":
        return RABBITMQ_QUEUE_HRBA_RAW
    return RABBITMQ_QUEUE_RAW_NF
