from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

TZ_BRASILIA = ZoneInfo("America/Sao_Paulo")


def now_brasilia() -> datetime:
    return datetime.now(TZ_BRASILIA)


def format_now_brasilia(fmt: str = "%d/%m/%Y %H:%M") -> str:
    return now_brasilia().strftime(fmt)
