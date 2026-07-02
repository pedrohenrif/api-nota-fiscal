from typing import Any

import httpx


def _join_messages(value: Any) -> str | None:
    if isinstance(value, list):
        parts = [str(item).strip() for item in value if str(item).strip()]
        return "; ".join(parts) if parts else None
    if value is not None and str(value).strip():
        return str(value).strip()
    return None


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

    erros_message = _join_messages(data.get("erros"))
    if erros_message:
        return erros_message

    for nested_key in ("data", "result", "retorno", "produto"):
        if nested_key in data:
            message = _extract_business_error(data[nested_key], _seen=seen)
            if message:
                return message

    for flag in ("sucesso", "success", "ok"):
        if flag in data and data[flag] is False:
            return "Operacao rejeitada pelo PR"

    return None


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
        raise ValueError(format_http_error(response))

    if not response.content:
        return {"status": "ok"}

    data = response.json()
    message = _extract_business_error(data)
    if message:
        raise ValueError(f"PR: {message}")

    return data
