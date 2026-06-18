import json
import time
from datetime import datetime, timedelta, timezone

import pika

from services.processor.config import (
    CONSUMER_IDLE_SLEEP_SECONDS,
    MAX_PROCESSING_RETRIES,
    RABBITMQ_QUEUE_DEAD,
    RABBITMQ_QUEUE_RAW_NF,
    RABBITMQ_URL,
    RETRY_DELAY_SECONDS,
)
from services.processor.db import SessionLocal
from services.processor.depara import apply_depara_rules
from services.processor.dispatcher import send_to_pr
from services.processor.migrations import parse_payload_metadata
from services.processor.repository import upsert_processing_status


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


def _schedule_retry(payload: dict) -> None:
    retries = int(payload.get("_retry_count", 0)) + 1
    payload["_retry_count"] = retries
    payload["_next_retry_at"] = (
        datetime.now(timezone.utc) + timedelta(seconds=RETRY_DELAY_SECONDS)
    ).isoformat()
    _publish(RABBITMQ_QUEUE_RAW_NF, payload)


def _publish_dead_letter(payload: dict, error_message: str) -> None:
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

        mapped_payload = apply_depara_rules(payload)
        send_to_pr(mapped_payload)
        upsert_processing_status(
            db,
            estabelecimento=estabelecimento,
            nf=nf,
            status="sent",
            tentativas=retries + 1,
            **meta,
        )
        return "sent"
    except Exception as exc:  # pragma: no cover
        error_message = str(exc)
        if retries + 1 >= MAX_PROCESSING_RETRIES:
            upsert_processing_status(
                db,
                estabelecimento=estabelecimento,
                nf=nf,
                status="dead_letter",
                tentativas=retries + 1,
                erro=error_message,
                **meta,
            )
            _publish_dead_letter(payload, error_message=error_message)
            return "dead_letter"
        upsert_processing_status(
            db,
            estabelecimento=estabelecimento,
            nf=nf,
            status="retry_pending",
            tentativas=retries + 1,
            erro=error_message,
            **meta,
        )
        _schedule_retry(payload)
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
            channel.basic_nack(delivery_tag=method_frame.delivery_tag, requeue=True)
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
            time.sleep(CONSUMER_IDLE_SLEEP_SECONDS)
            continue
        time.sleep(CONSUMER_IDLE_SLEEP_SECONDS)
