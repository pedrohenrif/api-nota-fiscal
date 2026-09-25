from threading import Event, Thread

from fastapi import FastAPI

from services.hrba_processor.config import (
    MAX_PROCESSING_RETRIES,
    MAX_RETRY_AGE_DAYS,
    ORACLE_HRBA_ENV,
    RABBITMQ_QUEUE_HRBA_RAW,
    RABBITMQ_URL,
    USE_MOCK_ORACLE,
)
from services.hrba_processor.consumer import consume_forever, consume_once
from services.processor.db import Base, engine
from services.processor.migrations import run_migrations

app = FastAPI(title="HRBA Processor Service")

Base.metadata.create_all(bind=engine)
run_migrations()
worker_stop_signal = Event()
worker_thread: Thread | None = None


@app.on_event("startup")
def startup_consumer() -> None:
    global worker_thread
    if worker_thread and worker_thread.is_alive():
        return
    worker_stop_signal.clear()
    worker_thread = Thread(
        target=consume_forever,
        args=(worker_stop_signal,),
        daemon=True,
        name="hrba-consumer-worker",
    )
    worker_thread.start()


@app.on_event("shutdown")
def shutdown_consumer() -> None:
    worker_stop_signal.set()


@app.get("/health")
def health() -> dict:
    running = worker_thread.is_alive() if worker_thread else False
    queue_depth = 0
    try:
        import pika

        connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
        try:
            channel = connection.channel()
            declared = channel.queue_declare(
                queue=RABBITMQ_QUEUE_HRBA_RAW, durable=True, passive=True
            )
            queue_depth = int(declared.method.message_count)
        finally:
            connection.close()
    except Exception:
        queue_depth = -1

    return {
        "status": "ok",
        "service": "hrba_processor",
        "destino": "tasy_hrba",
        "consumer_running": running,
        "oracle_hrba_env": ORACLE_HRBA_ENV,
        "use_mock_oracle": USE_MOCK_ORACLE,
        "max_retries": MAX_PROCESSING_RETRIES,
        "max_retry_age_days": MAX_RETRY_AGE_DAYS,
        "nf_hrba_raw_messages": queue_depth,
    }


@app.post("/consume")
def consume() -> dict:
    processed = consume_once()
    return {"processed_count": processed}
