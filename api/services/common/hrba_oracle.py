"""DSNs do canal HRBA.

Fonte (SEDE / estab 10): mesmo Oracle do PR (`ORACLE_DSN`), com override opcional
via `ORACLE_HRBA_SEDE_DSN_*` se precisar apontar outro banco.

Destino (Tasy HRBA): sempre `ORACLE_HRBA_DSN_*` — nunca o DSN do PR.
"""

from __future__ import annotations

import os

ORACLE_HRBA_ENV = os.getenv("ORACLE_HRBA_ENV", "homolog").lower()

# Override opcional da fonte SEDE (vazio = usa ORACLE_DSN do PR).
ORACLE_HRBA_SEDE_DSN_HOMOLOG = os.getenv("ORACLE_HRBA_SEDE_DSN_HOMOLOG", "").strip()
ORACLE_HRBA_SEDE_DSN_PRODUCTION = os.getenv("ORACLE_HRBA_SEDE_DSN_PRODUCTION", "").strip()

# Destino Tasy HRBA — homolog / production.
ORACLE_HRBA_DSN_HOMOLOG = os.getenv("ORACLE_HRBA_DSN_HOMOLOG", "").strip()
ORACLE_HRBA_DSN_PRODUCTION = os.getenv("ORACLE_HRBA_DSN_PRODUCTION", "").strip()


def get_hrba_sede_dsn() -> str:
    """Fonte das notas HRBA: override dedicado ou o mesmo ORACLE_DSN do PR."""
    override = (
        ORACLE_HRBA_SEDE_DSN_PRODUCTION
        if ORACLE_HRBA_ENV == "production"
        else ORACLE_HRBA_SEDE_DSN_HOMOLOG
    )
    if override:
        return override

    from services.extractor.config import ORACLE_DSN

    dsn = (ORACLE_DSN or "").strip()
    if not dsn:
        raise ValueError(
            "Fonte SEDE do HRBA: configure ORACLE_DSN (mesmo do PR) "
            "ou ORACLE_HRBA_SEDE_DSN_HOMOLOG / ORACLE_HRBA_SEDE_DSN_PRODUCTION"
        )
    return dsn


def sede_usa_oracle_dsn_pr() -> bool:
    """True quando a fonte SEDE esta caindo no ORACLE_DSN do PR (sem override)."""
    if ORACLE_HRBA_ENV == "production":
        return not bool(ORACLE_HRBA_SEDE_DSN_PRODUCTION)
    return not bool(ORACLE_HRBA_SEDE_DSN_HOMOLOG)


def get_hrba_destino_dsn() -> str:
    if ORACLE_HRBA_ENV == "production":
        if not ORACLE_HRBA_DSN_PRODUCTION:
            raise ValueError("ORACLE_HRBA_DSN_PRODUCTION nao configurado")
        return ORACLE_HRBA_DSN_PRODUCTION
    if not ORACLE_HRBA_DSN_HOMOLOG:
        raise ValueError("ORACLE_HRBA_DSN_HOMOLOG nao configurado")
    return ORACLE_HRBA_DSN_HOMOLOG
