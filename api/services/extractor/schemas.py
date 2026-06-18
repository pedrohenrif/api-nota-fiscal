from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class LoteNF(BaseModel):
    lote: str
    validade: Optional[datetime] = None
    observacao: Optional[str] = None
    qtdLote: float


class ProdutoNF(BaseModel):
    codProd: str
    cunit: float
    valor: float
    qtdEntrada: float
    loteNF: List[LoteNF] = Field(default_factory=list)


class FornecedorNF(BaseModel):
    cnpj: str


class NotaFiscalPRPayload(BaseModel):
    estabelecimento: str
    nrSequencia: Optional[str] = None
    nf: str
    serie: str
    fornecedor: FornecedorNF
    dataNF: datetime
    operador: str = "INTEGRACAO"
    doacao: bool = False
    vencimento: Optional[datetime] = None
    dataRecebimento: Optional[datetime] = None
    desconto: float = 0.0
    ipi: float = 0.0
    frete: float = 0.0
    valorTotal: float
    qtdItens: int
    produtos: List[ProdutoNF] = Field(default_factory=list)
