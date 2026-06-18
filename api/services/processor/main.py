from threading import Event, Thread

from fastapi import FastAPI

from services.processor.consumer import consume_forever, consume_once
from services.processor.db import Base, engine
from services.processor.migrations import run_migrations

app = FastAPI(title="Processor Service")

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
        name="processor-consumer-worker",
    )
    worker_thread.start()


@app.on_event("shutdown")
def shutdown_consumer() -> None:
    worker_stop_signal.set()


@app.get("/health")
def health() -> dict:
    running = worker_thread.is_alive() if worker_thread else False
    return {"status": "ok", "service": "processor", "consumer_running": running}


@app.post("/consume")
def consume() -> dict:
    processed = consume_once()
    return {"processed_count": processed}
