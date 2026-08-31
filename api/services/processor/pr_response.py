import unicodedata
from typing import Any

import httpx


def _normalize_text(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value.casefold())
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")


def is_pr_already_integrated_error(message: str | None) -> bool:
    """PR ja possui a NF+fornecedor (HTTP 400 negocio) — nao e falha de integracao."""
    if not message or not str(message).strip():
        return False
    text = _normalize_text(str(message))
    if "integracao.estoque.nf" in text and "movimento" in text:
        return True
    if "ja existe um lancamento" in text and "fornecedor" in text:
        return True
    if "mesma nf" in text and "fornecedor" in text and "ja existe" in text:
        return True
    return False


def _join_messages(value: Any) -> str | None:
    if isinstance(value, list):
        parts: list[str] = []
        seen: set[str] = set()
        for item in value:
            text = str(item).strip()
            if text and text not in seen:
                seen.add(text)
                parts.append(text)
        return "; ".join(parts) if parts else None
    if value is not None and str(value).strip():
        return str(value).strip()
    return None


def _is_pr_success(data: dict[str, Any]) -> bool:
    for flag in ("sucesso", "success", "ok"):
        if flag in data and data[flag] is True:
            return True
    return False


def _extract_business_error(data: Any, *, _seen: frozenset[int] | None = None) -> str | None:
    if isinstance(data, list):
        for item in data:
            message = _extract_business_error(item, _seen=_seen)
            if message:
                return message
        return None

    if not isinstance(data, dict):
        return None

    object_id = id(data)
    seen = _seen or frozenset()
    if object_id in seen:
        return None
    seen = seen | {object_id}

    if _is_pr_success(data):
        return None

    erros_message = _join_messages(data.get("erros"))
    if erros_message:
        return erros_message

    for key in (
        "erro",
        "error",
        "mensagem",
        "message",
        "mensagemErro",
        "detalhe",
        "detail",
        "descricao",
        "description",
    ):
        message = _join_messages(data.get(key))
        if message:
            return message

    for nested_key in ("data", "result", "retorno", "produto"):
        if nested_key in data:
            message = _extract_business_error(data[nested_key], _seen=seen)
            if message:
                return message

    for flag in ("sucesso", "success", "ok"):
        if flag in data and data[flag] is False:
            return "Operacao rejeitada pelo PR"

    return None


def extract_pr_success_info(data: Any) -> dict[str, Any] | None:
    if not isinstance(data, dict) or not _is_pr_success(data):
        return None

    pr_id = data.get("id")
    if pr_id is not None:
        try:
            pr_id = int(pr_id)
        except (TypeError, ValueError):
            pr_id = None

    mensagem = _join_messages(data.get("mensagem")) or _join_messages(data.get("message"))
    return {
        "pr_id": pr_id,
        "pr_mensagem": mensagem,
        "ja_existia_no_pr": bool(data.get("jaExistiaNoPR")),
    }


def format_http_error(response: httpx.Response) -> str:
    status = response.status_code
    try:
        body = response.json()
        message = _extract_business_error(body)
        if message:
            return f"PR HTTP {status}: {message}"
        return f"PR HTTP {status}: {body}"
    except ValueError:
        text = (response.text or "").strip()
        if text:
            return f"PR HTTP {status}: {text[:2000]}"
        return f"PR HTTP {status} ({response.reason_phrase})"


def parse_pr_response(response: httpx.Response) -> Any:
    if response.is_error:
        http_error = format_http_error(response)
        if is_pr_already_integrated_error(http_error):
            return {
                "sucesso": True,
                "jaExistiaNoPR": True,
                "mensagem": (
                    "Ja existe lancamento no PR com a mesma NF e FORNECEDOR; "
                    "tratado como integrado."
                ),
            }
        raise ValueError(http_error)

    if not response.content:
        return {"status": "ok"}

    data = response.json()
    message = _extract_business_error(data)
    if message:
        if is_pr_already_integrated_error(message):
            return {
                "sucesso": True,
                "jaExistiaNoPR": True,
                "mensagem": (
                    "Ja existe lancamento no PR com a mesma NF e FORNECEDOR; "
                    "tratado como integrado."
                ),
            }
        raise ValueError(f"PR: {message}")

    return data
