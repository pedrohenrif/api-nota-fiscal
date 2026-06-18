from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from services.processor.models import NotaProcessamento


def upsert_processing_status(
    db: Session,
    estabelecimento: str,
    nf: str,
    status: str,
    tentativas: int = 0,
    erro: str | None = None,
    nr_sequencia: str | None = None,
    fornecedor: str | None = None,
    data_nf: datetime | None = None,
) -> NotaProcessamento:
    query = db.query(NotaProcessamento).filter(
        NotaProcessamento.estabelecimento == estabelecimento
    )
    if nr_sequencia:
        record = query.filter(NotaProcessamento.nr_sequencia == nr_sequencia).first()
    else:
        record = query.filter(NotaProcessamento.nf == nf).first()

    if record is None:
        record = NotaProcessamento(
            estabelecimento=estabelecimento,
            nf=nf,
            nr_sequencia=nr_sequencia,
            fornecedor=fornecedor,
            data_nf=data_nf,
            status=status,
            tentativas=tentativas,
            erro=erro,
        )
        db.add(record)
    else:
        record.nf = nf
        record.nr_sequencia = nr_sequencia or record.nr_sequencia
        record.fornecedor = fornecedor or record.fornecedor
        record.data_nf = data_nf or record.data_nf
        record.status = status
        record.tentativas = tentativas
        record.erro = erro
    db.commit()
    db.refresh(record)
    return record
