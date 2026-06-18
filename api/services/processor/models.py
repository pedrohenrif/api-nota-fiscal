from sqlalchemy import Column, DateTime, Integer, String, Text, func

from services.processor.db import Base


class NotaProcessamento(Base):
    __tablename__ = "nota_processamento"

    id = Column(Integer, primary_key=True, autoincrement=True)
    estabelecimento = Column(String(80), nullable=False)
    nf = Column(String(80), nullable=False, index=True)
    nr_sequencia = Column(String(80), nullable=True, index=True)
    fornecedor = Column(String(20), nullable=True)
    data_nf = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(30), nullable=False, default="pending")
    tentativas = Column(Integer, nullable=False, default=0)
    erro = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
