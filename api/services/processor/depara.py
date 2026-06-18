from typing import Any

import httpx

from services.processor.config import PR_PRODUTO_DEPARA_PATH, get_pr_config
from services.processor.pr_response import parse_pr_response


def _extract_pr_product_code(response_data: Any) -> str:
    if isinstance(response_data, list):
        if not response_data:
            raise ValueError("Resposta de de-para vazia")
        return _extract_pr_product_code(response_data[0])

    if isinstance(response_data, dict):
        for key in ("codProd", "codigo", "codigoProduto", "CodProd", "Codigo", "id"):
            value = response_data.get(key)
            if value is not None and str(value).strip():
                return str(value).strip()
        for nested_key in ("produto", "data", "result"):
            if nested_key in response_data:
                return _extract_pr_product_code(response_data[nested_key])

    raise ValueError(f"Resposta de de-para sem codigo de produto: {response_data}")


def _map_product_code(
    client: httpx.Client, base_url: str, token: str, cod_material: str
) -> str:
    path = PR_PRODUTO_DEPARA_PATH.format(cod_vinculo=cod_material)
    url = f"{base_url}{path}"
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get(url, headers=headers)
    return _extract_pr_product_code(parse_pr_response(response))


def apply_depara_rules(payload: dict) -> dict:
    estabelecimento = payload.get("estabelecimento")
    if not estabelecimento:
        raise ValueError("Payload sem estabelecimento para de-para")

    pr_config = get_pr_config(estabelecimento)
    mapped = dict(payload)
    produtos = mapped.get("produtos") or []

    with httpx.Client(timeout=30.0) as client:
        for produto in produtos:
            cod_material = produto.get("codProd")
            if not cod_material:
                raise ValueError("Item da nota sem codProd (codigo material Tasy)")
            produto["codProd"] = _map_product_code(
                client=client,
                base_url=pr_config["base_url"],
                token=pr_config["token"],
                cod_material=str(cod_material),
            )

    return mapped
