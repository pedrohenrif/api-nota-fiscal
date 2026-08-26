from copy import deepcopy
from typing import Any

import httpx

from services.processor.config import PR_PRODUTO_DEPARA_PATH, build_pr_auth_headers, get_pr_config
from services.processor.pr_response import parse_pr_response


def _first_product_dict(response_data: Any) -> dict[str, Any]:
    if isinstance(response_data, list):
        if not response_data:
            raise ValueError("De-para vazio no PR.")
        return _first_product_dict(response_data[0])
    if isinstance(response_data, dict):
        for nested_key in ("produto", "data", "result"):
            if nested_key in response_data and response_data[nested_key] is not None:
                nested = response_data[nested_key]
                if isinstance(nested, (dict, list)):
                    return _first_product_dict(nested)
        return response_data
    raise ValueError(f"Resposta de de-para inesperada: {response_data}")


def _extract_pr_product_code(product: dict[str, Any], cod_material: str) -> str:
    # PR retorna CodProd (interno) e Cd_Integracao (codigo Tasy).
    for key in ("CodProd", "codProd", "codigo", "codigoProduto", "Codigo", "id"):
        value = product.get(key)
        if value is not None and str(value).strip():
            cod_pr = str(value).strip()
            if cod_pr == str(cod_material).strip():
                raise ValueError(
                    f"De-para retornou o mesmo codigo Tasy ({cod_material}) como codProd PR. "
                    "Verifique o vinculo no PR."
                )
            return cod_pr
    raise ValueError(
        f"De-para sem codigo PR para material Tasy codProd={cod_material}. "
        f"Resposta PR: {product}"
    )


def _extract_controle_de_lote(product: dict[str, Any]) -> bool:
    for key in ("ControleDeLote", "controleDeLote", "controle_de_lote"):
        if key in product:
            value = product.get(key)
            if isinstance(value, bool):
                return value
            if isinstance(value, (int, float)):
                return bool(value)
            if isinstance(value, str):
                return value.strip().lower() in {"1", "true", "s", "sim", "yes"}
    return False


def fetch_product_depara(
    client: httpx.Client, base_url: str, token: str, cod_material: str
) -> dict[str, Any]:
    """Consulta o PR e retorna codigo interno + flag ControleDeLote."""
    cod_material = str(cod_material).strip()
    path = PR_PRODUTO_DEPARA_PATH.format(cod_vinculo=cod_material)
    url = f"{base_url}{path}"
    headers = build_pr_auth_headers(token)
    response = client.get(url, headers=headers)
    parsed = parse_pr_response(response)
    try:
        product = _first_product_dict(parsed)
    except ValueError as exc:
        raise ValueError(
            f"De-para vazio no PR para material Tasy codProd={cod_material}. "
            "O codigo nao possui vinculo cadastrado no PR."
        ) from exc
    return {
        "codProdPR": _extract_pr_product_code(product, cod_material),
        "controleDeLote": _extract_controle_de_lote(product),
        "raw": product,
    }


def _map_product_code(
    client: httpx.Client, base_url: str, token: str, cod_material: str
) -> str:
    return fetch_product_depara(client, base_url, token, cod_material)["codProdPR"]


def check_product_depara(
    client: httpx.Client,
    base_url: str,
    token: str,
    cod_material: str,
) -> dict[str, Any]:
    cod_material = str(cod_material).strip()
    if not cod_material:
        return {
            "status": "erro",
            "codProdTasy": "",
            "codProdPR": None,
            "controleDeLote": False,
            "mensagem": "Item sem codProd (codigo material Tasy)",
        }

    try:
        info = fetch_product_depara(client, base_url, token, cod_material)
        return {
            "status": "ok",
            "codProdTasy": cod_material,
            "codProdPR": info["codProdPR"],
            "controleDeLote": bool(info["controleDeLote"]),
            "mensagem": None,
        }
    except ValueError as exc:
        message = str(exc)
        status = "vazio" if "vazio" in message.lower() else "erro"
        return {
            "status": status,
            "codProdTasy": cod_material,
            "codProdPR": None,
            "controleDeLote": False,
            "mensagem": message,
        }


def _lote_tem_codigo(lote: dict[str, Any]) -> bool:
    return bool(str(lote.get("lote") or "").strip())


def _lote_tem_validade(lote: dict[str, Any]) -> bool:
    validade = lote.get("validade")
    if validade is None:
        return False
    if isinstance(validade, str) and not validade.strip():
        return False
    return True


def _validate_lotes_obrigatorios(cod_material: str, lots: list[dict[str, Any]]) -> None:
    validos = [
        lot
        for lot in lots
        if _lote_tem_codigo(lot) and _lote_tem_validade(lot)
    ]
    if not validos:
        raise ValueError(
            f"Material Tasy {cod_material} exige controle de lote no PR "
            "(ControleDeLote=true), mas a nota nao possui lote com codigo e validade."
        )


def enrich_preview_with_depara(estabelecimento: str, preview: dict) -> tuple[dict, dict]:
    pr_config = get_pr_config(estabelecimento)
    produtos = preview.get("produtos") or []
    ok_count = 0
    fail_count = 0

    with httpx.Client(timeout=30.0) as client:
        for produto in produtos:
            depara = check_product_depara(
                client=client,
                base_url=pr_config["base_url"],
                token=pr_config["token"],
                cod_material=str(produto.get("codProd") or ""),
            )
            produto["depara"] = depara
            produto["controleDeLote"] = bool(depara.get("controleDeLote"))
            if depara["status"] == "ok":
                ok_count += 1
            else:
                fail_count += 1

    resumo = {"total": len(produtos), "ok": ok_count, "falha": fail_count}
    return preview, resumo


def apply_depara_rules(payload: dict) -> dict:
    estabelecimento = payload.get("estabelecimento")
    if not estabelecimento:
        raise ValueError("Payload sem estabelecimento para de-para")

    pr_config = get_pr_config(estabelecimento)
    mapped = deepcopy(payload)
    produtos = mapped.get("produtos") or []

    with httpx.Client(timeout=30.0) as client:
        for produto in produtos:
            cod_tasy = str(produto.get("codProdTasy") or produto.get("codProd") or "").strip()
            if not cod_tasy:
                raise ValueError("Item da nota sem codProd (codigo material Tasy)")

            info = fetch_product_depara(
                client=client,
                base_url=pr_config["base_url"],
                token=pr_config["token"],
                cod_material=cod_tasy,
            )
            controle_lote = bool(info["controleDeLote"])
            lots = list(produto.get("loteNF") or [])

            if controle_lote:
                _validate_lotes_obrigatorios(cod_tasy, lots)
                # Mantem apenas lotes completos (codigo + validade).
                produto["loteNF"] = [
                    lot
                    for lot in lots
                    if _lote_tem_codigo(lot) and _lote_tem_validade(lot)
                ]
            else:
                # Sem controle de lote: nao envia loteNF incompleto (evita validade "").
                produto["loteNF"] = []

            # POST /NF do PR usa codProd = codigo Tasy (Cd_Integracao), nao CodProd interno.
            produto["codProdTasy"] = cod_tasy
            produto["codProdPR"] = info["codProdPR"]
            produto["controleDeLote"] = controle_lote
            produto["codProd"] = cod_tasy

    return mapped
