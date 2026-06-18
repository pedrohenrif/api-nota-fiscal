from typing import Any

import httpx


def _extract_business_error(data: Any) -> str | None:
    if isinstance(data, list):
        for item in data:
            message = _extract_business_error(item)
            if message:
                return message
        return None

    if not isinstance(data, dict):
        return None

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
        value = data.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()

    for nested_key in ("data", "result", "retorno"):
        if nested_key in data:
            message = _extract_business_error(data[nested_key])
            if message:
                return message

    for flag in ("sucesso", "success", "ok"):
        if flag in data and data[flag] is False:
            return _extract_business_error(data) or "Operacao rejeitada pelo PR"

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

    if isinstance(data, dict):
        for flag in ("sucesso", "success"):
            if flag in data and data[flag] is False:
                raise ValueError(f"PR: {_extract_business_error(data) or 'Operacao rejeitada pelo PR'}")

    return data
