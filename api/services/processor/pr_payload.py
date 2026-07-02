from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

_NOTA_DATE_FIELDS = ("dataNF", "vencimento", "dataRecebimento")
_DATE_INPUT_FORMATS = (
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d",
    "%d/%m/%Y",
)


def _parse_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)
    if not isinstance(value, str):
        return None

    raw = value.strip()
    if not raw:
        return None

    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"

    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        pass

    for fmt in _DATE_INPUT_FORMATS:
        try:
            return datetime.strptime(value.strip(), fmt)
        except ValueError:
            continue

    return None


def format_pr_datetime(value: Any) -> str | None:
    parsed = _parse_datetime(value)
    if parsed is None:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    else:
        parsed = parsed.astimezone(timezone.utc)
    return parsed.isoformat().replace("+00:00", "Z")


def normalize_nota_for_pr(nota: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(nota)

    for field in _NOTA_DATE_FIELDS:
        if field in normalized and normalized[field] is not None:
            formatted = format_pr_datetime(normalized[field])
            if formatted is not None:
                normalized[field] = formatted

    produtos = normalized.get("produtos") or []
    for produto in produtos:
        produto.pop("depara", None)
        produto.pop("codProdTasy", None)
        for lote in produto.get("loteNF") or []:
            if lote.get("validade") is not None:
                formatted = format_pr_datetime(lote["validade"])
                if formatted is not None:
                    lote["validade"] = formatted

    return normalized


def build_pr_post_payload(payload: dict[str, Any]) -> dict[str, Any]:
    excluded = {"estabelecimento", "nrSequencia"}
    nota = {
        key: value
        for key, value in payload.items()
        if key not in excluded and not key.startswith("_")
    }
    return {"nota": normalize_nota_for_pr(nota)}
