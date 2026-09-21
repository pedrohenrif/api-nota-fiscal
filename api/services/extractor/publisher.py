import json
import logging

import pika

from services.extractor.config import (
    QUEUE_BACKPRESSURE_MAX,
    RABBITMQ_QUEUE_RAW_NF,
    RABBITMQ_URL,
)

logger = logging.getLogger(__name__)


def get_raw_queue_depth() -> int:
    params = pika.URLParameters(RABBITMQ_URL)
    connection = pika.BlockingConnection(params)
    try:
        channel = connection.channel()
        result = channel.queue_declare(queue=RABBITMQ_QUEUE_RAW_NF, durable=True, passive=True)
        return int(result.method.message_count)
    finally:
        connection.close()


def publish_raw_note(payload: dict) -> None:
    params = pika.URLParameters(RABBITMQ_URL)
    connection = pika.BlockingConnection(params)
    channel = connection.channel()
    channel.queue_declare(queue=RABBITMQ_QUEUE_RAW_NF, durable=True)
    channel.basic_publish(
        exchange="",
        routing_key=RABBITMQ_QUEUE_RAW_NF,
        body=json.dumps(payload, default=str).encode("utf-8"),
        properties=pika.BasicProperties(delivery_mode=2),
    )
    connection.close()


def should_pause_for_backpressure() -> tuple[bool, int]:
    """Pausa extracao automatica se a fila estiver acima do limite."""
    try:
        depth = get_raw_queue_depth()
    except Exception:
        logger.exception("Nao foi possivel consultar profundidade de %s", RABBITMQ_QUEUE_RAW_NF)
        return False, -1
    if depth >= QUEUE_BACKPRESSURE_MAX:
        return True, depth
    return False, depth
