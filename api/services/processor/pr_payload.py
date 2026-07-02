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
_LOTE_OBSERVACAO_DEFAULT = "-"


def _to_int(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    return int(round(float(value)))


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


def _format_date_field(nota: dict[str, Any], field: str) -> str | None:
    if field not in nota or nota[field] is None:
        return None
    return format_pr_datetime(nota[field])


def normalize_nota_for_pr(nota: dict[str, Any]) -> dict[str, Any]:
    """Normaliza payload interno (camelCase) para o contrato flat do PR."""
    normalized = dict(nota)

    for field in _NOTA_DATE_FIELDS:
        formatted = _format_date_field(normalized, field)
        if formatted is not None:
            normalized[field] = formatted

    data_nf = normalized.get("dataNF")
    if not normalized.get("vencimento") and data_nf:
        normalized["vencimento"] = data_nf
    if not normalized.get("dataRecebimento") and data_nf:
        normalized["dataRecebimento"] = data_nf

    normalized["operador"] = str(normalized.get("operador") or "INTEGRACAO").strip() or "INTEGRACAO"
    normalized["serie"] = str(normalized.get("serie") or "1").strip() or "1"
    normalized["nf"] = str(normalized.get("nf") or "").strip()
    normalized["doacao"] = bool(normalized.get("doacao", False))
    normalized["desconto"] = normalized.get("desconto", 0) or 0
    normalized["ipi"] = normalized.get("ipi", 0) or 0
    normalized["frete"] = normalized.get("frete", 0) or 0
    normalized["qtdItens"] = _to_int(normalized.get("qtdItens"))

    produtos = normalized.get("produtos") or []
    for produto in produtos:
        produto.pop("depara", None)
        produto.pop("codProdTasy", None)
        produto.pop("codProdPR", None)
        produto["codProd"] = str(produto.get("codProd") or "").strip()
        for lote in produto.get("loteNF") or []:
            if "qtdLote" in lote:
                lote["qtdLote"] = _to_int(lote.get("qtdLote"))
            if lote.get("validade") is not None:
                formatted = format_pr_datetime(lote["validade"])
                if formatted is not None:
                    lote["validade"] = formatted
            observacao = lote.get("observacao")
            if observacao is None or not str(observacao).strip():
                lote["observacao"] = _LOTE_OBSERVACAO_DEFAULT

    return normalized


def build_pr_post_payload(payload: dict[str, Any]) -> dict[str, Any]:
    excluded = {"estabelecimento", "nrSequencia"}
    nota = {
        key: value
        for key, value in payload.items()
        if key not in excluded and not key.startswith("_")
    }
    return normalize_nota_for_pr(nota)
