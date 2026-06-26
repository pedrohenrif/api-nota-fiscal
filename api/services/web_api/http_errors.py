import httpx
from fastapi import HTTPException


def raise_for_extractor_response(response: httpx.Response) -> None:
    if response.is_success:
        return

    fallback = "Nao foi possivel concluir a operacao no servico de extracao."
    try:
        payload = response.json()
        detail = payload.get("detail")
        if isinstance(detail, str) and detail.strip():
            fallback = detail.strip()
    except ValueError:
        pass

    status_code = response.status_code
    if status_code in (422, 503):
        raise HTTPException(status_code=status_code, detail=fallback)
    raise HTTPException(status_code=502, detail=fallback)
