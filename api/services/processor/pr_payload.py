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


def _map_keys(data: dict[str, Any], key_map: dict[str, str]) -> dict[str, Any]:
    mapped: dict[str, Any] = {}
    for key, value in data.items():
        if key.startswith("_"):
            continue
        mapped[key_map.get(key, key)] = value
    return mapped


def to_pr_nota_body(nota: dict[str, Any]) -> dict[str, Any]:
    """Converte payload interno (camelCase) para contrato PR (PascalCase)."""
    fornecedor = nota.get("fornecedor") or {}
    produtos = []
    for produto in nota.get("produtos") or []:
        lotes = [
            _map_keys(
                lote,
                {
                    "lote": "Lote",
                    "validade": "Validade",
                    "observacao": "Observacao",
                    "qtdLote": "QtdLote",
                },
            )
            for lote in produto.get("loteNF") or []
        ]
        produtos.append(
            _map_keys(
                {
                    "codProd": produto.get("codProd"),
                    "cunit": produto.get("cunit"),
                    "valor": produto.get("valor"),
                    "qtdEntrada": produto.get("qtdEntrada"),
                    "loteNF": lotes,
                },
                {
                    "codProd": "CodProd",
                    "cunit": "CUnit",
                    "valor": "Valor",
                    "qtdEntrada": "QtdEntrada",
                    "loteNF": "LoteNF",
                },
            )
        )

    return _map_keys(
        {
            "nf": nota.get("nf"),
            "serie": nota.get("serie"),
            "fornecedor": _map_keys(fornecedor, {"cnpj": "Cnpj"}),
            "dataNF": nota.get("dataNF"),
            "operador": nota.get("operador") or "INTEGRACAO",
            "doacao": bool(nota.get("doacao", False)),
            "vencimento": nota.get("vencimento"),
            "dataRecebimento": nota.get("dataRecebimento"),
            "desconto": nota.get("desconto", 0),
            "ipi": nota.get("ipi", 0),
            "frete": nota.get("frete", 0),
            "valorTotal": nota.get("valorTotal"),
            "qtdItens": nota.get("qtdItens"),
            "produtos": produtos,
        },
        {
            "nf": "NF",
            "serie": "Serie",
            "fornecedor": "Fornecedor",
            "dataNF": "DataNF",
            "operador": "Operador",
            "doacao": "Doacao",
            "vencimento": "Vencimento",
            "dataRecebimento": "DataRecebimento",
            "desconto": "Desconto",
            "ipi": "Ipi",
            "frete": "Frete",
            "valorTotal": "ValorTotal",
            "qtdItens": "QtdItens",
            "produtos": "Produtos",
        },
    )


def build_pr_post_payload(payload: dict[str, Any]) -> dict[str, Any]:
    excluded = {"estabelecimento", "nrSequencia"}
    nota = {
        key: value
        for key, value in payload.items()
        if key not in excluded and not key.startswith("_")
    }
    normalized = normalize_nota_for_pr(nota)
    return {"nota": to_pr_nota_body(normalized)}
