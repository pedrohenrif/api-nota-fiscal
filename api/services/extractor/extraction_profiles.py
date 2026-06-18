from dataclasses import dataclass


@dataclass(frozen=True)
class ExtractionProfile:
    estabelecimento_nome: str
    cd_estabelecimento: int
    dt_atualizacao_estoque_min: str
    dt_emissao_min: str
    cd_operacao_nf_in: tuple[int, ...]
    cd_operacao_nf_item_not_in: tuple[int, ...]


PROFILES = {
    "Castelo": ExtractionProfile(
        estabelecimento_nome="Castelo",
        cd_estabelecimento=9,
        dt_atualizacao_estoque_min="2025-09-21",
        dt_emissao_min="2024-05-14",
        cd_operacao_nf_in=(1, 39),
        cd_operacao_nf_item_not_in=(33,),
    ),
    "HRAS": ExtractionProfile(
        estabelecimento_nome="HRAS",
        cd_estabelecimento=9,
        dt_atualizacao_estoque_min="2025-09-21",
        dt_emissao_min="2024-05-14",
        cd_operacao_nf_in=(1, 39),
        cd_operacao_nf_item_not_in=(33,),
    ),
    "HRT": ExtractionProfile(
        estabelecimento_nome="HRT",
        cd_estabelecimento=9,
        dt_atualizacao_estoque_min="2025-09-21",
        dt_emissao_min="2024-05-14",
        cd_operacao_nf_in=(1, 39),
        cd_operacao_nf_item_not_in=(33,),
    ),
    "Ponta Pora": ExtractionProfile(
        estabelecimento_nome="Ponta Pora",
        cd_estabelecimento=9,
        dt_atualizacao_estoque_min="2025-09-21",
        dt_emissao_min="2024-05-14",
        cd_operacao_nf_in=(1, 39),
        cd_operacao_nf_item_not_in=(33,),
    ),
}
