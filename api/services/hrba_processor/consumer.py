from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timedelta, timezone
from threading import Event

import pika

from services.hrba_processor.config import (
    CONSUMER_IDLE_SLEEP_SECONDS,
    MAX_PROCESSING_RETRIES,
    MAX_RETRY_AGE_DAYS,
    PUBLISH_DEAD_LETTER_QUEUE,
    RABBITMQ_QUEUE_HRBA_DEAD,
    RABBITMQ_QUEUE_HRBA_RAW,
    RABBITMQ_URL,
    RETRY_BACKOFF_MAX_SECONDS,
    RETRY_DELAY_SECONDS,
)
from services.hrba_processor.worker import process_hrba_payload
from services.processor.db import SessionLocal
from services.processor.repository import upsert_processing_status
from services.hrba_processor.config import ESTABELECIMENTO_NOME

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
    if MAX_RETRY_AGE_DAYS <= 0:
        return False
    first = _ensure_first_attempt_at(payload)
    if first.tzinfo is None:
        first = first.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - first >= timedelta(days=MAX_RETRY_AGE_DAYS)


def _schedule_retry(payload: dict) -> None:
    retries = int(payload.get("_retry_count", 0)) + 1
    payload["_retry_count"] = retries
    _ensure_first_attempt_at(payload)
    delay = min(
        RETRY_DELAY_SECONDS * (2 ** max(retries - 1, 0)),
        RETRY_BACKOFF_MAX_SECONDS,
    )
    payload["_next_retry_at"] = (
        datetime.now(timezone.utc) + timedelta(seconds=delay)
    ).isoformat()
    _publish(RABBITMQ_QUEUE_HRBA_RAW, payload)


def _should_wait_retry(payload: dict) -> bool:
    next_retry_at = payload.get("_next_retry_at")
    if not next_retry_at:
        return False
    try:
        retry_dt = datetime.fromisoformat(next_retry_at)
    except ValueError:
        return False
    return retry_dt > datetime.now(timezone.utc)


def _publish_dead(payload: dict, reason: str) -> None:
    if not PUBLISH_DEAD_LETTER_QUEUE:
        return
    payload["_dead_letter_reason"] = reason
    payload["_dead_letter_at"] = datetime.now(timezone.utc).isoformat()
    _publish(RABBITMQ_QUEUE_HRBA_DEAD, payload)


def _handle_message(payload: dict) -> None:
    if _should_wait_retry(payload):
        _publish(RABBITMQ_QUEUE_HRBA_RAW, payload)
        time.sleep(0.5)
        return

    try:
        status = process_hrba_payload(payload)
    except Exception as exc:
        logger.exception("Falha HRBA: %s", exc)
        retries = int(payload.get("_retry_count", 0)) + 1
        payload["_retry_count"] = retries
        _ensure_first_attempt_at(payload)
        erro = str(exc)
        if retries >= MAX_PROCESSING_RETRIES or _retry_age_exceeded(payload):
            db = SessionLocal()
            try:
                meta_nf = str(payload.get("nf") or payload.get("nrSequencia") or "?")
                upsert_processing_status(
                    db,
                    estabelecimento=ESTABELECIMENTO_NOME,
                    nf=meta_nf,
                    status="dead_letter",
                    tentativas=retries,
                    erro=erro,
                    erro_tipo="outro",
                    nr_sequencia=str(payload.get("nrSequencia") or "") or None,
                )
            finally:
                db.close()
            _publish_dead(payload, erro)
            return
        _schedule_retry(payload)
        return

    if status == "retry_pending":
        retries = int(payload.get("_retry_count", 0)) + 1
        if retries >= MAX_PROCESSING_RETRIES or _retry_age_exceeded(payload):
            db = SessionLocal()
            try:
                upsert_processing_status(
                    db,
                    estabelecimento=ESTABELECIMENTO_NOME,
                    nf=str(payload.get("nf") or "?"),
                    status="dead_letter",
                    tentativas=retries,
                    erro="Esgotadas tentativas de integracao HRBA",
                    erro_tipo="estoque_nao_atualizado",
                    nr_sequencia=str(payload.get("nrSequencia") or "") or None,
                )
            finally:
                db.close()
            _publish_dead(payload, "retry esgotado")
            return
        _schedule_retry(payload)


def consume_once() -> int:
    connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
    try:
        channel = connection.channel()
        channel.queue_declare(queue=RABBITMQ_QUEUE_HRBA_RAW, durable=True)
        method, _props, body = channel.basic_get(queue=RABBITMQ_QUEUE_HRBA_RAW, auto_ack=False)
        if method is None:
            return 0
        try:
            payload = json.loads(body.decode("utf-8"))
            _handle_message(payload)
            channel.basic_ack(method.delivery_tag)
            return 1
        except Exception:
            channel.basic_nack(method.delivery_tag, requeue=False)
            raise
    finally:
        connection.close()


def consume_forever(stop_signal: Event) -> None:
    logger.info("HRBA consumer iniciado | fila=%s", RABBITMQ_QUEUE_HRBA_RAW)
    while not stop_signal.is_set():
        try:
            processed = consume_once()
            if processed == 0:
                stop_signal.wait(timeout=CONSUMER_IDLE_SLEEP_SECONDS)
        except Exception:
            logger.exception("Erro no loop HRBA consumer")
            stop_signal.wait(timeout=CONSUMER_IDLE_SLEEP_SECONDS)
