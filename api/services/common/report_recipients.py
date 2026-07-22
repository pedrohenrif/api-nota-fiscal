from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import Column, DateTime, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Session

from services.common.estab_config import Base, SessionLocal, engine
from services.common.estabelecimentos import ESTABELECIMENTOS

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

_EMAIL_ENV_KEYS = {
    "Castelo": "REPORT_EMAIL_CASTELO",
    "HRAS": "REPORT_EMAIL_HRAS",
    "HRT": "REPORT_EMAIL_HRT",
    "Ponta Pora": "REPORT_EMAIL_PONTA_PORA",
}


class ReportDestinatario(Base):
    __tablename__ = "report_destinatario"
    __table_args__ = (
        UniqueConstraint(
            "estabelecimento",
            "email",
            name="uq_report_destinatario_estab_email",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    estabelecimento = Column(String(80), nullable=False, index=True)
    email = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


_table_ready = False


def ensure_report_recipients_table() -> None:
    global _table_ready
    if _table_ready:
        return
    Base.metadata.create_all(bind=engine, tables=[ReportDestinatario.__table__])
    _seed_from_env_if_empty()
    _table_ready = True


def _normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def validate_email(email: str) -> str:
    normalized = _normalize_email(email)
    if not normalized or not _EMAIL_RE.match(normalized):
        raise ValueError("E-mail invalido")
    if len(normalized) > 255:
        raise ValueError("E-mail muito longo")
    return normalized


def _env_emails(estabelecimento: str) -> list[str]:
    key = _EMAIL_ENV_KEYS.get(estabelecimento)
    if not key:
        return []
    raw = os.getenv(key, "")
    return [_normalize_email(part) for part in raw.split(",") if part.strip()]


def _seed_from_env_if_empty() -> None:
    db = SessionLocal()
    try:
        count = db.query(ReportDestinatario).count()
        if count > 0:
            return
        now = datetime.now(timezone.utc)
        for estab in ESTABELECIMENTOS:
            for email in _env_emails(estab):
                try:
                    email = validate_email(email)
                except ValueError:
                    continue
                db.add(
                    ReportDestinatario(
                        estabelecimento=estab,
                        email=email,
                        created_at=now,
                        updated_at=now,
                    )
                )
        db.commit()
    finally:
        db.close()


def get_recipients(estabelecimento: str) -> list[str]:
    """Lista destinatarios do banco; fallback para .env se tabela vazia na unidade."""
    ensure_report_recipients_table()
    db = SessionLocal()
    try:
        rows = (
            db.query(ReportDestinatario.email)
            .filter(ReportDestinatario.estabelecimento == estabelecimento)
            .order_by(ReportDestinatario.email.asc())
            .all()
        )
        emails = [str(r[0]) for r in rows if r[0]]
        if emails:
            return emails
        return _env_emails(estabelecimento)
    finally:
        db.close()


def list_recipients(
    *,
    estabelecimento: Optional[str] = None,
    db: Session | None = None,
) -> list[dict[str, Any]]:
    ensure_report_recipients_table()
    own = db is None
    session = db or SessionLocal()
    try:
        query = session.query(ReportDestinatario)
        if estabelecimento:
            query = query.filter(ReportDestinatario.estabelecimento == estabelecimento)
        rows = query.order_by(
            ReportDestinatario.estabelecimento.asc(),
            ReportDestinatario.email.asc(),
        ).all()
        return [
            {
                "id": row.id,
                "estabelecimento": row.estabelecimento,
                "email": row.email,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            }
            for row in rows
        ]
    finally:
        if own:
            session.close()


def create_recipient(
    *,
    estabelecimento: str,
    email: str,
    db: Session | None = None,
) -> dict[str, Any]:
    ensure_report_recipients_table()
    if estabelecimento not in ESTABELECIMENTOS:
        raise ValueError("Estabelecimento invalido")
    normalized = validate_email(email)
    own = db is None
    session = db or SessionLocal()
    try:
        exists = (
            session.query(ReportDestinatario)
            .filter(
                ReportDestinatario.estabelecimento == estabelecimento,
                ReportDestinatario.email == normalized,
            )
            .first()
        )
        if exists:
            raise ValueError("E-mail ja cadastrado para este estabelecimento")
        row = ReportDestinatario(estabelecimento=estabelecimento, email=normalized)
        session.add(row)
        session.commit()
        session.refresh(row)
        return {
            "id": row.id,
            "estabelecimento": row.estabelecimento,
            "email": row.email,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }
    except Exception:
        session.rollback()
        raise
    finally:
        if own:
            session.close()


def update_recipient(
    *,
    recipient_id: int,
    email: str,
    allowed_estabelecimento: Optional[str] = None,
    db: Session | None = None,
) -> dict[str, Any]:
    ensure_report_recipients_table()
    normalized = validate_email(email)
    own = db is None
    session = db or SessionLocal()
    try:
        row = (
            session.query(ReportDestinatario)
            .filter(ReportDestinatario.id == recipient_id)
            .first()
        )
        if row is None:
            raise LookupError("Destinatario nao encontrado")
        if allowed_estabelecimento and row.estabelecimento != allowed_estabelecimento:
            raise PermissionError("Sem permissao para este estabelecimento")
        duplicate = (
            session.query(ReportDestinatario)
            .filter(
                ReportDestinatario.estabelecimento == row.estabelecimento,
                ReportDestinatario.email == normalized,
                ReportDestinatario.id != recipient_id,
            )
            .first()
        )
        if duplicate:
            raise ValueError("E-mail ja cadastrado para este estabelecimento")
        row.email = normalized
        session.commit()
        session.refresh(row)
        return {
            "id": row.id,
            "estabelecimento": row.estabelecimento,
            "email": row.email,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }
    except Exception:
        session.rollback()
        raise
    finally:
        if own:
            session.close()


def delete_recipient(
    *,
    recipient_id: int,
    allowed_estabelecimento: Optional[str] = None,
    db: Session | None = None,
) -> None:
    ensure_report_recipients_table()
    own = db is None
    session = db or SessionLocal()
    try:
        row = (
            session.query(ReportDestinatario)
            .filter(ReportDestinatario.id == recipient_id)
            .first()
        )
        if row is None:
            raise LookupError("Destinatario nao encontrado")
        if allowed_estabelecimento and row.estabelecimento != allowed_estabelecimento:
            raise PermissionError("Sem permissao para este estabelecimento")
        session.delete(row)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        if own:
            session.close()
