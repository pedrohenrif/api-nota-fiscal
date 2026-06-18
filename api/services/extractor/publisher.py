import json

import pika

from services.extractor.config import RABBITMQ_QUEUE_RAW_NF, RABBITMQ_URL


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
