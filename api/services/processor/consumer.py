import json
import logging
import time
from datetime import datetime, timedelta, timezone

import pika

from services.processor.config import (
    CONSUMER_IDLE_SLEEP_SECONDS,
    MAX_PROCESSING_RETRIES,
    PR_CIRCUIT_RETRY_DELAY_SECONDS,
    PUBLISH_DEAD_LETTER_QUEUE,
    RABBITMQ_QUEUE_DEAD,
    RABBITMQ_QUEUE_RAW_NF,
    RABBITMQ_URL,
    RETRY_BACKOFF_MAX_SECONDS,
    RETRY_DELAY_SECONDS,
)
from services.processor.db import SessionLocal
from services.processor.depara import apply_depara_rules
from services.processor.dispatcher import send_to_pr
from services.processor.error_tipo import classify_error_tipo
from services.processor.migrations import parse_payload_metadata
from services.processor.pr_circuit import is_pr_timeout_error, pr_circuit
from services.processor.pr_response import extract_pr_success_info
from services.processor.repository import get_sent_record, upsert_processing_status
from services.processor.runtime_stats import runtime_stats
from services.processor.tasy_writeback import mark_tasy_integrated

logger = logging.getLogger(__name__)


def _publish(queue_name: str, payload: dict) -> None:
    connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
    try:
        channel = connection.channel()
        channel.queue_declare(queue=queue_name, durable=True)
        channel.basic_publish(
            exchange="",
            routing_key=queue_name,
            body=json.dumps(payload, default=str).encode("utf-8"),
            properties=pika.BasicProperties(delivery_mode=2),
        )
    finally:
        connection.close()


def _should_wait_retry(payload: dict) -> bool:
    next_retry_at = payload.get("_next_retry_at")
    if not next_retry_at:
        return False
    try:
        retry_dt = datetime.fromisoformat(next_retry_at)
    except ValueError:
        return False
    return retry_dt > datetime.now(timezone.utc)


def _retry_delay_seconds(retries_after_increment: int, *, circuit_open: bool = False) -> int:
    if circuit_open:
        return max(PR_CIRCUIT_RETRY_DELAY_SECONDS, RETRY_DELAY_SECONDS)
    # backoff exponencial: 10, 20, 40... ate o teto
    delay = RETRY_DELAY_SECONDS * (2 ** max(retries_after_increment - 1, 0))
    return min(delay, RETRY_BACKOFF_MAX_SECONDS)


def _schedule_retry(payload: dict, *, circuit_open: bool = False) -> None:
    retries = int(payload.get("_retry_count", 0)) + 1
    payload["_retry_count"] = retries
    delay = _retry_delay_seconds(retries, circuit_open=circuit_open)
    payload["_next_retry_at"] = (
        datetime.now(timezone.utc) + timedelta(seconds=delay)
    ).isoformat()
    _publish(RABBITMQ_QUEUE_RAW_NF, payload)


def _republish_deferred(payload: dict) -> None:
    """Recoloca no fim da fila sem incrementar tentativas (espera _next_retry_at)."""
    _publish(RABBITMQ_QUEUE_RAW_NF, payload)


def _publish_dead_letter(payload: dict, error_message: str) -> None:
    if not PUBLISH_DEAD_LETTER_QUEUE:
        return
    payload["_dead_letter_reason"] = error_message
    payload["_dead_letter_at"] = datetime.now(timezone.utc).isoformat()
    _publish(RABBITMQ_QUEUE_DEAD, payload)


def _status_kwargs(payload: dict) -> dict:
    nr_sequencia, fornecedor, data_nf = parse_payload_metadata(payload)
    return {
        "nr_sequencia": nr_sequencia,
        "fornecedor": fornecedor,
        "data_nf": data_nf,
    }


def process_payload(payload: dict) -> str:
    estabelecimento = payload.get("estabelecimento", "")
    nf = payload.get("nf", "")
    retries = int(payload.get("_retry_count", 0))
    meta = _status_kwargs(payload)
    db = SessionLocal()
    try:
        if _should_wait_retry(payload):
            return "defer"

        already_sent = get_sent_record(
            db,
            estabelecimento=estabelecimento,
            nf=nf,
            nr_sequencia=meta.get("nr_sequencia"),
        )
        if already_sent is not None:
            logger.info(
                "Nota ja enviada (sent) — ignorando reprocessamento nf=%s seq=%s",
                nf,
                meta.get("nr_sequencia"),
            )
            runtime_stats.record_success(nf=nf, result="sent_idempotent")
            return "sent"

        if not pr_circuit.allow_request():
            snap = pr_circuit.snapshot()
            error_message = (
                "PR circuit breaker aberto apos timeouts consecutivos "
                f"({snap['open_remaining_seconds']}s restantes)."
            )
            upsert_processing_status(
                db,
                estabelecimento=estabelecimento,
                nf=nf,
                status="retry_pending",
                tentativas=retries,
                erro=error_message,
                erro_tipo="timeout_pr",
                **meta,
            )
            _schedule_retry(payload, circuit_open=True)
            runtime_stats.record_failure(
                nf=nf, result="circuit_open", error=error_message
            )
            return "retry_scheduled"

        mapped_payload = apply_depara_rules(payload)
        pr_result = send_to_pr(mapped_payload)
        success_info = extract_pr_success_info(pr_result) or {}
        ja_existia_no_pr = bool(success_info.get("ja_existia_no_pr"))
        if ja_existia_no_pr:
            logger.info(
                "PR ja possui NF+fornecedor — write-back Tasy e status sent nf=%s seq=%s",
                nf,
                meta.get("nr_sequencia"),
            )

        tasy_warning = None
        try:
            mark_tasy_integrated(meta.get("nr_sequencia"))
        except Exception as writeback_exc:
            tasy_warning = str(writeback_exc)
            logger.error(
                "PR OK (ja_existia=%s), mas write-back Tasy falhou: %s",
                ja_existia_no_pr,
                tasy_warning,
            )

        pr_mensagem = success_info.get("pr_mensagem")
        if ja_existia_no_pr and not pr_mensagem:
            pr_mensagem = (
                "Ja existe lancamento no PR com a mesma NF e FORNECEDOR; "
                "tratado como integrado."
            )
        if tasy_warning:
            pr_mensagem = (
                f"{pr_mensagem or 'Nota gravada no PR'}; "
                f"alerta Tasy: {tasy_warning}"
            )

        upsert_processing_status(
            db,
            estabelecimento=estabelecimento,
            nf=nf,
            status="sent",
            tentativas=retries + 1,
            erro=None,
            erro_tipo=None,
            pr_id=success_info.get("pr_id"),
            pr_mensagem=pr_mensagem,
            **meta,
        )
        runtime_stats.record_success(nf=nf, result="sent")
        return "sent"
    except Exception as exc:  # pragma: no cover
        error_message = str(exc)
        erro_tipo = classify_error_tipo(error_message)
        if retries + 1 >= MAX_PROCESSING_RETRIES:
            upsert_processing_status(
                db,
                estabelecimento=estabelecimento,
                nf=nf,
                status="dead_letter",
                tentativas=retries + 1,
                erro=error_message,
                erro_tipo=erro_tipo,
                **meta,
            )
            _publish_dead_letter(payload, error_message=error_message)
            runtime_stats.record_failure(
                nf=nf, result="dead_letter", error=error_message
            )
            return "dead_letter"
        upsert_processing_status(
            db,
            estabelecimento=estabelecimento,
            nf=nf,
            status="retry_pending",
            tentativas=retries + 1,
            erro=error_message,
            erro_tipo=erro_tipo,
            **meta,
        )
        _schedule_retry(payload, circuit_open=is_pr_timeout_error(error_message))
        runtime_stats.record_failure(
            nf=nf, result="retry_scheduled", error=error_message
        )
        return "retry_scheduled"
    finally:
        db.close()


def consume_once() -> int:
    processed = 0
    params = pika.URLParameters(RABBITMQ_URL)
    connection = pika.BlockingConnection(params)
    channel = connection.channel()
    channel.queue_declare(queue=RABBITMQ_QUEUE_RAW_NF, durable=True)

    method_frame, _, body = channel.basic_get(queue=RABBITMQ_QUEUE_RAW_NF, auto_ack=False)
    if method_frame:
        payload = json.loads(body.decode("utf-8"))
        result = process_payload(payload)
        if result == "defer":
            # Nao faz nack+requeue (volta para a cabeca e trava a fila).
            # Ack + republica no fim, respeitando _next_retry_at.
            channel.basic_ack(delivery_tag=method_frame.delivery_tag)
            _republish_deferred(payload)
            processed = 1
        else:
            channel.basic_ack(delivery_tag=method_frame.delivery_tag)
            processed = 1

    connection.close()
    return processed


def consume_forever(stop_signal) -> None:
    while not stop_signal.is_set():
        try:
            consume_once()
        except Exception:
            logger.exception("Falha no loop do consumer")
            time.sleep(CONSUMER_IDLE_SLEEP_SECONDS)
            continue
        time.sleep(CONSUMER_IDLE_SLEEP_SECONDS)
