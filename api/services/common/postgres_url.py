"""Normaliza DSN Postgres para o driver instalado no projeto (psycopg2)."""

from __future__ import annotations


def normalize_postgres_url(url: str) -> str:
    raw = (url or "").strip()
    if not raw:
        return raw
    # SQLAlchemy recente pode mapear postgresql:// -> psycopg (v3).
    # O projeto usa psycopg2-binary.
    if raw.startswith("postgresql+psycopg://"):
        return "postgresql+psycopg2://" + raw[len("postgresql+psycopg://") :]
    if raw.startswith("postgresql://"):
        return "postgresql+psycopg2://" + raw[len("postgresql://") :]
    if raw.startswith("postgres://"):
        return "postgresql+psycopg2://" + raw[len("postgres://") :]
    return raw
