from fastapi import FastAPI, HTTPException
from threading import Event, Lock, Thread

from services.extractor.config import (
    EXTRACTION_RUN_ON_STARTUP,
    EXTRACTION_SCHEDULER_ENABLED,
    POLL_INTERVAL_MINUTES,
    USE_MOCK_ORACLE,
)
from services.extractor.extractor import (
    MockOracleClient,
    consult_note_by_nr_sequencia,
    extract_pending_notes,
    extract_single_note,
)
from services.extractor.publisher import publish_raw_note

app = FastAPI(title="Extractor Service")

ESTABELECIMENTOS = ["Castelo", "HRAS", "HRT", "Ponta Pora"]
scheduler_stop_signal = Event()
scheduler_lock = Lock()
scheduler_thread: Thread | None = None


@app.get("/health")
def health() -> dict:
    running = scheduler_thread.is_alive() if scheduler_thread else False
    return {
        "status": "ok",
        "service": "extractor",
        "scheduler_enabled": EXTRACTION_SCHEDULER_ENABLED,
        "scheduler_running": running,
        "poll_interval_minutes": POLL_INTERVAL_MINUTES,
    }


def _run_extraction_cycle(estabelecimento: str | None = None) -> dict:
    targets = [estabelecimento] if estabelecimento else ESTABELECIMENTOS
    published = 0
    oracle_client = MockOracleClient() if USE_MOCK_ORACLE else None
    for target in targets:
        notes = extract_pending_notes(estabelecimento=target, db_client=oracle_client)
        for note in notes:
            publish_raw_note(note.model_dump())
            published += 1
    return {"published_count": published, "estabelecimentos": targets}


def _scheduler_loop() -> None:
    interval_seconds = max(POLL_INTERVAL_MINUTES, 1) * 60
    if EXTRACTION_RUN_ON_STARTUP:
        with scheduler_lock:
            _run_extraction_cycle()

    while not scheduler_stop_signal.wait(timeout=interval_seconds):
        if scheduler_stop_signal.is_set():
            break
        with scheduler_lock:
            _run_extraction_cycle()


@app.on_event("startup")
def startup_scheduler() -> None:
    global scheduler_thread
    if not EXTRACTION_SCHEDULER_ENABLED:
        return
    if scheduler_thread and scheduler_thread.is_alive():
        return
    scheduler_stop_signal.clear()
    scheduler_thread = Thread(
        target=_scheduler_loop,
        daemon=True,
        name="extractor-scheduler-worker",
    )
    scheduler_thread.start()


@app.on_event("shutdown")
def shutdown_scheduler() -> None:
    scheduler_stop_signal.set()


@app.post("/run")
def run_extraction(estabelecimento: str | None = None) -> dict:
    with scheduler_lock:
        return _run_extraction_cycle(estabelecimento=estabelecimento)


@app.get("/preview")
def preview_extraction(estabelecimento: str) -> dict:
    oracle_client = MockOracleClient() if USE_MOCK_ORACLE else None
    notes = extract_pending_notes(estabelecimento=estabelecimento, db_client=oracle_client)
    payloads = [note.model_dump(mode="json") for note in notes]
    return {"count": len(payloads), "notes": payloads}


@app.get("/notas/consultar")
def consultar_nota(estabelecimento: str, nr_sequencia: str) -> dict:
    if estabelecimento not in ESTABELECIMENTOS:
        return {"encontrada": False, "valido": False, "mensagem": "Estabelecimento invalido."}
    oracle_client = MockOracleClient() if USE_MOCK_ORACLE else None
    return consult_note_by_nr_sequencia(
        estabelecimento=estabelecimento,
        nr_sequencia=nr_sequencia,
        db_client=oracle_client,
    )


@app.post("/notas/emitir-especifica")
def emitir_nota_especifica(estabelecimento: str, nr_sequencia: str) -> dict:
    if estabelecimento not in ESTABELECIMENTOS:
        raise HTTPException(status_code=422, detail="Estabelecimento invalido")
    oracle_client = MockOracleClient() if USE_MOCK_ORACLE else None
    try:
        note = extract_single_note(
            estabelecimento=estabelecimento,
            nr_sequencia=nr_sequencia,
            db_client=oracle_client,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    publish_raw_note(note.model_dump())
    return {
        "estabelecimento": estabelecimento,
        "nr_sequencia": nr_sequencia,
        "nf": note.nf,
        "published": True,
    }
