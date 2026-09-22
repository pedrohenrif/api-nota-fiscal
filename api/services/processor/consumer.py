import json
import logging
import time
from datetime import datetime, timedelta, timezone

import pika

from services.processor.config import (
    CONSUMER_IDLE_SLEEP_SECONDS,
    MAX_PROCESSING_RETRIES,
    MAX_RETRY_AGE_DAYS,
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


def _ensure_first_attempt_at(payload: dict) -> datetime:
    raw = payload.get("_first_attempt_at")
    if isinstance(raw, str) and raw:
        try:
            return datetime.fromisoformat(raw)
        except ValueError:
            pass
    now = datetime.now(timezone.utc)
    payload["_first_attempt_at"] = now.isoformat()
    return now


def _retry_age_exceeded(payload: dict) -> bool:
    """True se a nota ja passou do prazo maximo de retry (default 2 dias)."""
    if MAX_RETRY_AGE_DAYS <= 0:
        return False
    first = _ensure_first_attempt_at(payload)
    if first.tzinfo is None:
        first = first.replace(tzinfo=timezone.utc)
    age = datetime.now(timezone.utc) - first
    return age >= timedelta(days=MAX_RETRY_AGE_DAYS)


def _dead_letter_age_message() -> str:
    days = MAX_RETRY_AGE_DAYS
    days_label = int(days) if float(days).is_integer() else days
    return (
        f"Prazo maximo de retry excedido ({days_label} dia(s)). "
        "Nota movida para dead_letter — reprocessar manualmente no painel apos corrigir a causa."
    )


def _retry_delay_seconds(retries_after_increment: int, *, circuit_open: bool = False) -> int:
    if circuit_open:
        return max(PR_CIRCUIT_RETRY_DELAY_SECONDS, RETRY_DELAY_SECONDS)
    # backoff exponencial: 10, 20, 40... ate o teto
    delay = RETRY_DELAY_SECONDS * (2 ** max(retries_after_increment - 1, 0))
    return min(delay, RETRY_BACKOFF_MAX_SECONDS)


def _schedule_retry(payload: dict, *, circuit_open: bool = False) -> None:
    retries = int(payload.get("_retry_count", 0)) + 1
    payload["_retry_count"] = retries
    _ensure_first_attempt_at(payload)
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


def _mark_dead_letter(
    db,
    *,
    payload: dict,
    estabelecimento: str,
    nf: str,
    retries: int,
    error_message: str,
    erro_tipo: str | None,
    meta: dict,
) -> str:
    upsert_processing_status(
        db,
        estabelecimento=estabelecimento,
        nf=nf,
        status="dead_letter",
        tentativas=retries,
        erro=error_message,
        erro_tipo=erro_tipo,
        **meta,
    )
    _publish_dead_letter(payload, error_message=error_message)
    runtime_stats.record_failure(nf=nf, result="dead_letter", error=error_message)
    return "dead_letter"


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
            if _retry_age_exceeded(payload):
                return _mark_dead_letter(
                    db,
                    payload=payload,
                    estabelecimento=estabelecimento,
                    nf=nf,
                    retries=retries,
                    error_message=_dead_letter_age_message(),
                    erro_tipo="timeout_pr",
                    meta=meta,
                )
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
            _ensure_first_attempt_at(payload)
            if _retry_age_exceeded(payload):
                return _mark_dead_letter(
                    db,
                    payload=payload,
                    estabelecimento=estabelecimento,
                    nf=nf,
                    retries=retries,
                    error_message=_dead_letter_age_message(),
                    erro_tipo="timeout_pr",
                    meta=meta,
                )
            # Nao incrementa tentativa nem republica com retry++ (isso inchava a fila).
            snap = pr_circuit.snapshot()
            wait_s = max(int(snap.get("open_remaining_seconds") or 0), PR_CIRCUIT_RETRY_DELAY_SECONDS)
            payload["_next_retry_at"] = (
                datetime.now(timezone.utc) + timedelta(seconds=wait_s)
            ).isoformat()
            error_message = (
                "PR circuit breaker aberto apos timeouts consecutivos "
                f"({snap.get('open_remaining_seconds', 0)}s restantes). "
                "Consumer em pausa/backpressure."
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
            runtime_stats.record_failure(
                nf=nf, result="circuit_open", error=error_message
            )
            return "defer"

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
        _ensure_first_attempt_at(payload)
        next_retries = retries + 1
        is_timeout = is_pr_timeout_error(error_message) or erro_tipo == "timeout_pr"
        # Timeout/PR lento: so encerra por prazo (2 dias). Outros erros: esgota por contagem.
        age_exceeded = _retry_age_exceeded(payload)
        count_exceeded = (not is_timeout) and next_retries >= MAX_PROCESSING_RETRIES

        if age_exceeded or count_exceeded:
            final_error = (
                f"{_dead_letter_age_message()} Ultimo erro: {error_message}"
                if age_exceeded
                else error_message
            )
            return _mark_dead_letter(
                db,
                payload=payload,
                estabelecimento=estabelecimento,
                nf=nf,
                retries=next_retries,
                error_message=final_error,
                erro_tipo=erro_tipo,
                meta=meta,
            )

        upsert_processing_status(
            db,
            estabelecimento=estabelecimento,
            nf=nf,
            status="retry_pending",
            tentativas=next_retries,
            erro=error_message,
            erro_tipo=erro_tipo,
            **meta,
        )
        _schedule_retry(payload, circuit_open=is_timeout)
        runtime_stats.record_failure(
            nf=nf, result="retry_scheduled", error=error_message
        )
        return "retry_scheduled"
    finally:
        db.close()


def _sleep_while_circuit_open() -> bool:
    """Se o circuit estiver aberto, dorme ate fechar. Retorna True se dormiu."""
    if pr_circuit.allow_request():
        return False
    snap = pr_circuit.snapshot()
    wait_s = max(int(snap.get("open_remaining_seconds") or 0), 5)
    logger.warning(
        "Circuit breaker PR aberto — pausando consumer por %ss (sem drenar/republicar fila)",
        wait_s,
    )
    time.sleep(wait_s)
    return True


def consume_once() -> int:
    runtime_stats.record_heartbeat()
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
            # Backpressure: com PR fora (circuit aberto), nao gira a fila inteira.
            if _sleep_while_circuit_open():
                continue
            consume_once()
        except Exception:
            logger.exception("Falha no loop do consumer")
            time.sleep(CONSUMER_IDLE_SLEEP_SECONDS)
            continue
        time.sleep(CONSUMER_IDLE_SLEEP_SECONDS)
