import httpx

from services.processor.config import PR_NF_PATH, get_pr_config
from services.processor.pr_response import parse_pr_response


def build_pr_post_payload(payload: dict) -> dict:
    excluded = {"estabelecimento", "nrSequencia"}
    return {key: value for key, value in payload.items() if key not in excluded and not key.startswith("_")}


def send_to_pr(payload: dict) -> dict:
    estabelecimento = payload.get("estabelecimento")
    if not estabelecimento:
        raise ValueError("Payload sem estabelecimento")

    pr_config = get_pr_config(estabelecimento)
    url = f"{pr_config['base_url']}{PR_NF_PATH}"
    headers = {"Authorization": f"Bearer {pr_config['token']}"}
    body = build_pr_post_payload(payload)

    with httpx.Client(timeout=30.0) as client:
        response = client.post(url, json=body, headers=headers)
        return parse_pr_response(response)
