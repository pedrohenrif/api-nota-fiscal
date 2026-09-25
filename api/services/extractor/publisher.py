import json
import logging

import pika

from services.extractor.config import (
    QUEUE_BACKPRESSURE_MAX,
    RABBITMQ_QUEUE_HRBA_RAW,
    RABBITMQ_QUEUE_RAW_NF,
    RABBITMQ_URL,
)
from services.extractor.extraction_profiles import PROFILES, queue_name_for_estabelecimento

logger = logging.getLogger(__name__)


def get_queue_depth(queue_name: str) -> int:
    params = pika.URLParameters(RABBITMQ_URL)
    connection = pika.BlockingConnection(params)
    try:
        channel = connection.channel()
        result = channel.queue_declare(queue=queue_name, durable=True, passive=True)
        return int(result.method.message_count)
    finally:
        connection.close()


def get_raw_queue_depth() -> int:
    return get_queue_depth(RABBITMQ_QUEUE_RAW_NF)


def publish_to_queue(payload: dict, queue_name: str) -> None:
    params = pika.URLParameters(RABBITMQ_URL)
    connection = pika.BlockingConnection(params)
    channel = connection.channel()
    channel.queue_declare(queue=queue_name, durable=True)
    channel.basic_publish(
        exchange="",
        routing_key=queue_name,
        body=json.dumps(payload, default=str).encode("utf-8"),
        properties=pika.BasicProperties(delivery_mode=2),
    )
    connection.close()


def publish_raw_note(payload: dict, estabelecimento: str | None = None) -> None:
    """
    Publica nota na fila correta conforme o perfil do estabelecimento.
    HRBA -> nf.hrba.raw; demais -> nf.raw.
    """
    estab = estabelecimento or payload.get("estabelecimento")
    queue_name = (
        queue_name_for_estabelecimento(str(estab))
        if estab
        else RABBITMQ_QUEUE_RAW_NF
    )
    profile = PROFILES.get(str(estab)) if estab else None
    enriched = dict(payload)
    enriched["_destino"] = profile.destino if profile else "pr"
    publish_to_queue(enriched, queue_name)
    logger.info(
        "Nota publicada | estab=%s nf=%s fila=%s destino=%s",
        estab,
        enriched.get("nf"),
        queue_name,
        enriched.get("_destino"),
    )


def should_pause_for_backpressure() -> tuple[bool, int]:
    """Pausa extracao automatica se a fila PR estiver acima do limite."""
    try:
        depth = get_raw_queue_depth()
    except Exception:
        logger.exception("Nao foi possivel consultar profundidade de %s", RABBITMQ_QUEUE_RAW_NF)
        return False, -1
    if depth >= QUEUE_BACKPRESSURE_MAX:
        return True, depth
    # Tambem observa backlog HRBA (limite compartilhado).
    try:
        hrba_depth = get_queue_depth(RABBITMQ_QUEUE_HRBA_RAW)
        if hrba_depth >= QUEUE_BACKPRESSURE_MAX:
            return True, hrba_depth
    except Exception:
        pass
    return False, depth
