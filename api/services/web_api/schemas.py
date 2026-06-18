from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

Role = Literal["adm", "usuario"]


class LoginRequest(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UsuarioCreate(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=4, max_length=128)
    role: Role = "usuario"
    estabelecimento: Optional[str] = None


class UsuarioOut(BaseModel):
    id: int
    username: str
    role: Role
    estabelecimento: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class EmitirNotaRequest(BaseModel):
    estabelecimento: Optional[str] = None


class EmitirNotaEspecificaRequest(BaseModel):
    estabelecimento: Optional[str] = None
    nr_sequencia: str = Field(min_length=1, max_length=80)


class ReemitirNotaRequest(BaseModel):
    id: int


class NotaConsultaOut(BaseModel):
    encontrada: bool
    valido: bool
    mensagem: Optional[str] = None
    nr_sequencia: Optional[str] = None
    nf: Optional[str] = None
    cd_operacao_nf: Optional[int] = None
    operacoes_liberadas: list[int] = Field(default_factory=list)
    fornecedor: Optional[str] = None
    data_nf: Optional[datetime] = None
    qtd_itens: Optional[int] = None


class NotaStatusOut(BaseModel):
    id: int
    estabelecimento: str
    nf: str
    nr_sequencia: Optional[str] = None
    fornecedor: Optional[str] = None
    data_nf: Optional[datetime] = None
    status: str
    tentativas: int
    erro: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
