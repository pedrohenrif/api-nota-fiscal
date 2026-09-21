from __future__ import annotations

import json
import logging
import time
from typing import Any

import httpx

from services.processor.config import (
    PR_DEBUG_HTTP,
    PR_HTTP_TIMEOUT_SECONDS,
    PR_NF_PATH,
    build_pr_auth_headers,
    get_pr_config,
)
from services.processor.pr_circuit import is_pr_timeout_error, pr_circuit
from services.processor.pr_payload import build_pr_post_payload
from services.processor.pr_response import parse_pr_response

logger = logging.getLogger(__name__)

_MAX_BODY_LOG_CHARS = 8000


def _clip(text: str, limit: int = _MAX_BODY_LOG_CHARS) -> str:
    if len(text) <= limit:
        return text
    return f"{text[:limit]}… [truncated {len(text) - limit} chars]"


def _safe_json(data: Any) -> str:
    try:
        return json.dumps(data, ensure_ascii=False, default=str)
    except Exception:
        return str(data)


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

    nf = payload.get("nf") or body.get("nf") or body.get("NF")
    nr_seq = payload.get("nrSequencia") or body.get("nrSequencia")
    debug = PR_DEBUG_HTTP

    if debug:
        logger.info(
            "[PR DEBUG] POST inicio estab=%s nf=%s nr_sequencia=%s url=%s timeout=%ss",
            estabelecimento,
            nf,
            nr_seq,
            url,
            PR_HTTP_TIMEOUT_SECONDS,
        )
        logger.info("[PR DEBUG] request body=%s", _clip(_safe_json(body)))

    started = time.perf_counter()
    try:
        with httpx.Client(timeout=PR_HTTP_TIMEOUT_SECONDS) as client:
            response = client.post(url, json=body, headers=headers)
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            if debug:
                raw_text = response.text or ""
                logger.info(
                    "[PR DEBUG] POST resposta estab=%s nf=%s status=%s elapsed_ms=%s "
                    "content_type=%s body_len=%s",
                    estabelecimento,
                    nf,
                    response.status_code,
                    elapsed_ms,
                    response.headers.get("content-type"),
                    len(raw_text),
                )
                logger.info("[PR DEBUG] response body=%s", _clip(raw_text))
            parsed = parse_pr_response(response)
    except Exception as exc:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        logger.error(
            "[PR DEBUG] POST falhou estab=%s nf=%s nr_sequencia=%s elapsed_ms=%s erro=%s",
            estabelecimento,
            nf,
            nr_seq,
            elapsed_ms,
            exc,
        )
        pr_circuit.record_failure(is_timeout=is_pr_timeout_error(str(exc)))
        raise

    pr_circuit.record_success()
    if debug:
        logger.info(
            "[PR DEBUG] POST ok/parseado estab=%s nf=%s keys=%s",
            estabelecimento,
            nf,
            list(parsed.keys()) if isinstance(parsed, dict) else type(parsed).__name__,
        )
    return parsed
