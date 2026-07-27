from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True)
class ExtractionProfile:
    estabelecimento_nome: str
    cd_estabelecimento: int
    dt_emissao_min: str
    cd_operacao_nf_in: tuple[int, ...]
    cd_operacao_nf_item_not_in: tuple[int, ...]
    # Janela móvel: só notas com dt_atualizacao_estoque >= (hoje - N dias).
    dt_atualizacao_estoque_lookback_days: int = 31

    @property
    def dt_atualizacao_estoque_min(self) -> str:
        """Data mínima inclusiva recalculada a cada extração (YYYY-MM-DD)."""
        return (
            date.today()
            - timedelta(days=self.dt_atualizacao_estoque_lookback_days)
        ).isoformat()


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
}
