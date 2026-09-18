from __future__ import annotations

import httpx

from services.processor.config import (
    PR_HTTP_TIMEOUT_SECONDS,
    PR_NF_PATH,
    build_pr_auth_headers,
    get_pr_config,
)
from services.processor.pr_circuit import is_pr_timeout_error, pr_circuit
from services.processor.pr_payload import build_pr_post_payload
from services.processor.pr_response import parse_pr_response


def send_to_pr(payload: dict) -> dict:
    estabelecimento = payload.get("estabelecimento")
    if not estabelecimento:
        raise ValueError("Payload sem estabelecimento")

    if not pr_circuit.allow_request():
        snap = pr_circuit.snapshot()
        raise RuntimeError(
            "PR circuit breaker aberto "
            f"({snap['open_remaining_seconds']}s restantes apos timeouts consecutivos). "
            "Nova tentativa sera agendada."
        )

    pr_config = get_pr_config(estabelecimento)
    url = f"{pr_config['base_url']}{PR_NF_PATH}"
    headers = build_pr_auth_headers(pr_config["token"])
    body = build_pr_post_payload(payload)

    try:
        with httpx.Client(timeout=PR_HTTP_TIMEOUT_SECONDS) as client:
            response = client.post(url, json=body, headers=headers)
            parsed = parse_pr_response(response)
    except Exception as exc:
        pr_circuit.record_failure(is_timeout=is_pr_timeout_error(str(exc)))
        raise

    pr_circuit.record_success()
    return parsed
