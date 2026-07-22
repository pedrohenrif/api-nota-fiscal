from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable

from sqlalchemy import Column, DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Session

from services.common.estab_config import Base, SessionLocal, engine

# Categorias enviadas uma unica vez no e-mail.
ONCE_CATEGORIES = frozenset({"integradas", "erros_pr", "nao_integradas"})
# Categorias que podem repetir a cada ciclo (pendencias operacionais).
REPEAT_CATEGORIES = frozenset({"sem_depara", "sem_lote"})


class NotaReportEnvio(Base):
    __tablename__ = "nota_report_envio"
    __table_args__ = (
        UniqueConstraint(
            "estabelecimento",
            "chave",
            "categoria",
            name="uq_nota_report_envio_estab_chave_cat",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    estabelecimento = Column(String(80), nullable=False, index=True)
    chave = Column(String(80), nullable=False)  # nr_sequencia ou nf
    nr_sequencia = Column(String(80), nullable=True)
    nf = Column(String(80), nullable=True)
    categoria = Column(String(40), nullable=False, index=True)
    enviado_em = Column(DateTime(timezone=True), nullable=False)


_table_ready = False


def ensure_report_sent_table() -> None:
    global _table_ready
    if _table_ready:
        return
    Base.metadata.create_all(
        bind=engine,
        tables=[NotaReportEnvio.__table__],
    )
    _table_ready = True


def _item_key(item: dict[str, Any]) -> str:
    return str(item.get("nr_sequencia") or item.get("nf") or "").strip()


def already_reported_keys(
    estabelecimento: str,
    categoria: str,
    db: Session | None = None,
) -> set[str]:
    ensure_report_sent_table()
    own = db is None
    session = db or SessionLocal()
    try:
        rows = (
            session.query(NotaReportEnvio.chave)
            .filter(
                NotaReportEnvio.estabelecimento == estabelecimento,
                NotaReportEnvio.categoria == categoria,
            )
            .all()
        )
        return {str(row[0]) for row in rows if row[0]}
    finally:
        if own:
            session.close()


def filter_unreported(
    estabelecimento: str,
    categoria: str,
    items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if categoria not in ONCE_CATEGORIES:
        return items
    reported = already_reported_keys(estabelecimento, categoria)
    if not reported:
        return items
    return [item for item in items if _item_key(item) not in reported]


def mark_reported(
    estabelecimento: str,
    categoria: str,
    items: Iterable[dict[str, Any]],
) -> int:
    if categoria not in ONCE_CATEGORIES:
        return 0
    ensure_report_sent_table()
    now = datetime.now(timezone.utc)
    inserted = 0
    db = SessionLocal()
    try:
        for item in items:
            chave = _item_key(item)
            if not chave:
                continue
            exists = (
                db.query(NotaReportEnvio.id)
                .filter(
                    NotaReportEnvio.estabelecimento == estabelecimento,
                    NotaReportEnvio.chave == chave,
                    NotaReportEnvio.categoria == categoria,
                )
                .first()
            )
            if exists:
                continue
            db.add(
                NotaReportEnvio(
                    estabelecimento=estabelecimento,
                    chave=chave,
                    nr_sequencia=str(item.get("nr_sequencia") or "") or None,
                    nf=str(item.get("nf") or "") or None,
                    categoria=categoria,
                    enviado_em=now,
                )
            )
            inserted += 1
        db.commit()
        return inserted
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def mark_report_sent(estabelecimento: str, report: dict[str, Any]) -> dict[str, int]:
    """Persiste o que foi incluido nas categorias once-only apos SMTP OK."""
    result: dict[str, int] = {}
    for categoria in ONCE_CATEGORIES:
        items = report.get(categoria) or []
        result[categoria] = mark_reported(estabelecimento, categoria, items)
    return result
