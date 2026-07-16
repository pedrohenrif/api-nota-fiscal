from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from services.processor.models import NotaProcessamento


def get_sent_record(
    db: Session,
    estabelecimento: str,
    nf: str,
    nr_sequencia: str | None = None,
) -> NotaProcessamento | None:
    query = db.query(NotaProcessamento).filter(
        NotaProcessamento.estabelecimento == estabelecimento,
        NotaProcessamento.status == "sent",
    )
    if nr_sequencia:
        return query.filter(NotaProcessamento.nr_sequencia == nr_sequencia).first()
    return query.filter(NotaProcessamento.nf == nf).first()


def upsert_processing_status(
    db: Session,
    estabelecimento: str,
    nf: str,
    status: str,
    tentativas: int = 0,
    erro: str | None = None,
    erro_tipo: str | None = None,
    pr_id: int | None = None,
    pr_mensagem: str | None = None,
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
            erro_tipo=erro_tipo,
            pr_id=pr_id,
            pr_mensagem=pr_mensagem,
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
        record.erro_tipo = erro_tipo
        if pr_id is not None:
            record.pr_id = pr_id
        if pr_mensagem is not None:
            record.pr_mensagem = pr_mensagem
        if status == "sent":
            record.erro = None
            record.erro_tipo = None
    db.commit()
    db.refresh(record)
    return record
