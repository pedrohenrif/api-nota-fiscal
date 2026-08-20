"""Configuracoes globais persistidas (ex.: intervalo do relatorio por e-mail)."""

from __future__ import annotations

import os

from sqlalchemy import Column, DateTime, String, text
from sqlalchemy.orm import Session

from services.common.estab_config import Base, SessionLocal, engine

REPORT_INTERVAL_KEY = "report_interval_minutes"
ALLOWED_REPORT_INTERVALS = frozenset({6, 30})
_ENV_FALLBACK = int(os.getenv("REPORT_INTERVAL_MINUTES", "6"))


class AppSetting(Base):
    __tablename__ = "app_setting"

    key = Column(String(80), primary_key=True)
    value = Column(String(255), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
        onupdate=text("NOW()"),
    )


_table_ready = False


def ensure_app_settings_table() -> None:
    global _table_ready
    if _table_ready:
        return
    Base.metadata.create_all(bind=engine, tables=[AppSetting.__table__])
    _table_ready = True


def get_report_interval_minutes(db: Session | None = None) -> int:
    ensure_app_settings_table()
    own = db is None
    session = db or SessionLocal()
    try:
        row = session.get(AppSetting, REPORT_INTERVAL_KEY)
        if row and str(row.value).isdigit():
            value = int(row.value)
            if value in ALLOWED_REPORT_INTERVALS:
                return value
        return (
            _ENV_FALLBACK
            if _ENV_FALLBACK in ALLOWED_REPORT_INTERVALS
            else 6
        )
    finally:
        if own:
            session.close()


def set_report_interval_minutes(minutes: int, db: Session | None = None) -> int:
    if minutes not in ALLOWED_REPORT_INTERVALS:
        raise ValueError(
            f"Intervalo invalido: {minutes}. Use um de {sorted(ALLOWED_REPORT_INTERVALS)}."
        )
    ensure_app_settings_table()
    own = db is None
    session = db or SessionLocal()
    try:
        row = session.get(AppSetting, REPORT_INTERVAL_KEY)
        if row is None:
            row = AppSetting(key=REPORT_INTERVAL_KEY, value=str(minutes))
            session.add(row)
        else:
            row.value = str(minutes)
        session.commit()
        return minutes
    except Exception:
        session.rollback()
        raise
    finally:
        if own:
            session.close()
