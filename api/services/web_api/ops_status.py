from __future__ import annotations

from typing import Any

import httpx
import pika

from services.web_api.config import (
    PROCESSOR_URL,
    RABBITMQ_QUEUE_DEAD,
    RABBITMQ_QUEUE_RAW_NF,
    RABBITMQ_URL,
)


def _queue_depth(queue_name: str) -> dict[str, Any]:
    connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
    try:
        channel = connection.channel()
        result = channel.queue_declare(queue=queue_name, durable=True, passive=True)
        return {
            "name": queue_name,
            "messages": int(result.method.message_count),
            "consumers": int(result.method.consumer_count),
        }
    finally:
        connection.close()


def _processor_health() -> dict[str, Any]:
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(f"{PROCESSOR_URL.rstrip('/')}/health")
            if response.is_error:
                return {
                    "ok": False,
                    "error": f"HTTP {response.status_code}",
                }
            data = response.json()
            data["ok"] = True
            return data
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def get_filas_status() -> dict[str, Any]:
    raw = _queue_depth(RABBITMQ_QUEUE_RAW_NF)
    dead = _queue_depth(RABBITMQ_QUEUE_DEAD)
    processor = _processor_health()

    raw_messages = int(raw.get("messages") or 0)
    stalled = bool(processor.get("processor_stalled")) and raw_messages > 0
    circuit_open = bool(processor.get("circuit_open"))
    consumer_running = bool(processor.get("consumer_running"))

    alerts: list[str] = []
    if not processor.get("ok"):
        alerts.append("Processor indisponivel ou sem health.")
    elif not consumer_running:
        alerts.append("Consumer do processor nao esta rodando.")
    if circuit_open:
        alerts.append("Circuit breaker do PR aberto (timeouts consecutivos).")
    if stalled:
        alerts.append(
            f"Processor sem atividade com {raw_messages} msg na fila — possivel travamento."
        )
    if raw_messages >= 100:
        alerts.append(f"Fila nf.raw com {raw_messages} mensagens — backlog alto.")
    elif raw_messages >= 20:
        alerts.append(f"Fila nf.raw com {raw_messages} mensagens.")

    return {
        "nf_raw": raw,
        "nf_dead": dead,
        "processor": processor,
        "alerts": alerts,
        "healthy": len(alerts) == 0,
    }
