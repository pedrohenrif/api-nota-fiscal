"""DSNs Oracle exclusivos do canal HRBA (SEDE fonte + HRBA destino).

Nao reutiliza ORACLE_DSN do fluxo PR — assim homolog HRBA nao le/escreve prod.
"""

from __future__ import annotations

import os

ORACLE_HRBA_ENV = os.getenv("ORACLE_HRBA_ENV", "homolog").lower()

# SEDE (fonte das notas do estab 10) — homolog / production separados do PR.
ORACLE_HRBA_SEDE_DSN_HOMOLOG = os.getenv("ORACLE_HRBA_SEDE_DSN_HOMOLOG", "").strip()
ORACLE_HRBA_SEDE_DSN_PRODUCTION = os.getenv("ORACLE_HRBA_SEDE_DSN_PRODUCTION", "").strip()

# HRBA (destino Tasy) — homolog / production.
ORACLE_HRBA_DSN_HOMOLOG = os.getenv("ORACLE_HRBA_DSN_HOMOLOG", "").strip()
ORACLE_HRBA_DSN_PRODUCTION = os.getenv("ORACLE_HRBA_DSN_PRODUCTION", "").strip()


def get_hrba_sede_dsn() -> str:
    if ORACLE_HRBA_ENV == "production":
        if not ORACLE_HRBA_SEDE_DSN_PRODUCTION:
            raise ValueError(
                "ORACLE_HRBA_SEDE_DSN_PRODUCTION nao configurado "
                "(SEDE de producao do canal HRBA; nao use ORACLE_DSN do PR)"
            )
        return ORACLE_HRBA_SEDE_DSN_PRODUCTION
    if not ORACLE_HRBA_SEDE_DSN_HOMOLOG:
        raise ValueError(
            "ORACLE_HRBA_SEDE_DSN_HOMOLOG nao configurado "
            "(SEDE de homolog do canal HRBA; nao use ORACLE_DSN do PR)"
        )
    return ORACLE_HRBA_SEDE_DSN_HOMOLOG


def get_hrba_destino_dsn() -> str:
    if ORACLE_HRBA_ENV == "production":
        if not ORACLE_HRBA_DSN_PRODUCTION:
            raise ValueError("ORACLE_HRBA_DSN_PRODUCTION nao configurado")
        return ORACLE_HRBA_DSN_PRODUCTION
    if not ORACLE_HRBA_DSN_HOMOLOG:
        raise ValueError("ORACLE_HRBA_DSN_HOMOLOG nao configurado")
    return ORACLE_HRBA_DSN_HOMOLOG
