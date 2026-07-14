from __future__ import annotations

import os
from typing import Any

from sqlalchemy import Boolean, Column, DateTime, String, create_engine, func, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from services.common.estabelecimentos import ESTABELECIMENTOS

POSTGRES_URL = os.getenv("POSTGRES_URL", "postgresql://tasy:tasy@localhost:5432/tasy_db")

Base = declarative_base()
engine = create_engine(POSTGRES_URL, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class EstabelecimentoConfig(Base):
    __tablename__ = "estabelecimento_config"

    estabelecimento = Column(String(80), primary_key=True)
    scheduler_enabled = Column(Boolean, nullable=False, default=False)
    report_enabled = Column(Boolean, nullable=False, default=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


_table_ready = False


def ensure_estab_config_table() -> None:
    global _table_ready
    if _table_ready:
        return
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                ALTER TABLE estabelecimento_config
                ADD COLUMN IF NOT EXISTS scheduler_enabled BOOLEAN NOT NULL DEFAULT FALSE
                """
            )
        )
        conn.execute(
            text(
                """
                ALTER TABLE estabelecimento_config
                ADD COLUMN IF NOT EXISTS report_enabled BOOLEAN NOT NULL DEFAULT FALSE
                """
            )
        )
    seed_estabelecimento_config()
    _table_ready = True


def seed_estabelecimento_config() -> None:
    db = SessionLocal()
    try:
        for nome in ESTABELECIMENTOS:
            existing = (
                db.query(EstabelecimentoConfig)
                .filter(EstabelecimentoConfig.estabelecimento == nome)
                .first()
            )
            if existing is None:
                db.add(
                    EstabelecimentoConfig(
                        estabelecimento=nome,
                        scheduler_enabled=False,
                        report_enabled=False,
                    )
                )
        db.commit()
    finally:
        db.close()


def list_estab_configs(db: Session | None = None) -> list[dict[str, Any]]:
    own_session = db is None
    session = db or SessionLocal()
    try:
        ensure_estab_config_table()
        rows = (
            session.query(EstabelecimentoConfig)
            .order_by(EstabelecimentoConfig.estabelecimento.asc())
            .all()
        )
        by_name = {row.estabelecimento: row for row in rows}
        result: list[dict[str, Any]] = []
        for nome in ESTABELECIMENTOS:
            row = by_name.get(nome)
            if row is None:
                result.append(
                    {
                        "estabelecimento": nome,
                        "scheduler_enabled": False,
                        "report_enabled": False,
                        "updated_at": None,
                    }
                )
            else:
                result.append(
                    {
                        "estabelecimento": row.estabelecimento,
                        "scheduler_enabled": bool(row.scheduler_enabled),
                        "report_enabled": bool(row.report_enabled),
                        "updated_at": row.updated_at,
                    }
                )
        return result
    finally:
        if own_session:
            session.close()


def get_estab_config(estabelecimento: str, db: Session | None = None) -> dict[str, Any] | None:
    if estabelecimento not in ESTABELECIMENTOS:
        return None
    own_session = db is None
    session = db or SessionLocal()
    try:
        ensure_estab_config_table()
        row = (
            session.query(EstabelecimentoConfig)
            .filter(EstabelecimentoConfig.estabelecimento == estabelecimento)
            .first()
        )
        if row is None:
            return {
                "estabelecimento": estabelecimento,
                "scheduler_enabled": False,
                "report_enabled": False,
                "updated_at": None,
            }
        return {
            "estabelecimento": row.estabelecimento,
            "scheduler_enabled": bool(row.scheduler_enabled),
            "report_enabled": bool(row.report_enabled),
            "updated_at": row.updated_at,
        }
    finally:
        if own_session:
            session.close()


def update_estab_config(
    estabelecimento: str,
    *,
    scheduler_enabled: bool | None = None,
    report_enabled: bool | None = None,
    db: Session | None = None,
) -> dict[str, Any] | None:
    if estabelecimento not in ESTABELECIMENTOS:
        return None
    own_session = db is None
    session = db or SessionLocal()
    try:
        ensure_estab_config_table()
        row = (
            session.query(EstabelecimentoConfig)
            .filter(EstabelecimentoConfig.estabelecimento == estabelecimento)
            .first()
        )
        if row is None:
            row = EstabelecimentoConfig(
                estabelecimento=estabelecimento,
                scheduler_enabled=False,
                report_enabled=False,
            )
            session.add(row)
        if scheduler_enabled is not None:
            row.scheduler_enabled = scheduler_enabled
        if report_enabled is not None:
            row.report_enabled = report_enabled
        session.commit()
        session.refresh(row)
        return {
            "estabelecimento": row.estabelecimento,
            "scheduler_enabled": bool(row.scheduler_enabled),
            "report_enabled": bool(row.report_enabled),
            "updated_at": row.updated_at,
        }
    finally:
        if own_session:
            session.close()


def list_scheduler_enabled() -> list[str]:
    return [
        item["estabelecimento"]
        for item in list_estab_configs()
        if item.get("scheduler_enabled")
    ]


def list_report_enabled() -> list[str]:
    return [
        item["estabelecimento"]
        for item in list_estab_configs()
        if item.get("report_enabled")
    ]
