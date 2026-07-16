import logging

from fastapi import FastAPI, HTTPException
from threading import Event, Lock, Thread

from services.common.estabelecimentos import ESTABELECIMENTOS
from services.common.estab_config import ensure_estab_config_table, list_scheduler_enabled
from services.extractor.config import (
    EXTRACTION_RUN_ON_STARTUP,
    EXTRACTION_SCHEDULER_ENABLED,
    POLL_INTERVAL_MINUTES,
    USE_MOCK_ORACLE,
)
from services.extractor.errors import friendly_oracle_error
from services.extractor.extractor import (
    MockOracleClient,
    consult_note_by_nr_sequencia,
    extract_pending_notes,
    extract_single_note,
    mark_note_integrated,
)
from services.extractor.publisher import publish_raw_note

logger = logging.getLogger(__name__)

app = FastAPI(title="Extractor Service")

scheduler_stop_signal = Event()
scheduler_lock = Lock()
scheduler_thread: Thread | None = None


@app.get("/health")
def health() -> dict:
    running = scheduler_thread.is_alive() if scheduler_thread else False
    enabled_targets = list_scheduler_enabled() if EXTRACTION_SCHEDULER_ENABLED else []
    return {
        "status": "ok",
        "service": "extractor",
        "scheduler_enabled": EXTRACTION_SCHEDULER_ENABLED,
        "scheduler_running": running,
        "poll_interval_minutes": POLL_INTERVAL_MINUTES,
        "scheduler_estabelecimentos": enabled_targets,
    }


def _run_extraction_cycle(estabelecimento: str | None = None) -> dict:
    if estabelecimento:
        targets = [estabelecimento]
    else:
        # Ciclo automatico: apenas unidades com scheduler_enabled=true no Postgres.
        targets = list_scheduler_enabled()
    published = 0
    errors: list[dict] = []
    oracle_client = MockOracleClient() if USE_MOCK_ORACLE else None
    for target in targets:
        try:
            notes = extract_pending_notes(estabelecimento=target, db_client=oracle_client)
            for note in notes:
                publish_raw_note(note.model_dump(mode="json"))
                published += 1
        except Exception as exc:
            logger.exception("Falha no ciclo de extracao para %s: %s", target, exc)
            errors.append({"estabelecimento": target, "erro": str(exc)})
    return {
        "published_count": published,
        "estabelecimentos": targets,
        "errors": errors,
    }


def _scheduler_loop() -> None:
    interval_seconds = max(POLL_INTERVAL_MINUTES, 1) * 60
    if EXTRACTION_RUN_ON_STARTUP:
        with scheduler_lock:
            try:
                _run_extraction_cycle()
            except Exception:
                logger.exception("Falha no ciclo inicial do scheduler")

    while not scheduler_stop_signal.wait(timeout=interval_seconds):
        if scheduler_stop_signal.is_set():
            break
        with scheduler_lock:
            try:
                _run_extraction_cycle()
            except Exception:
                logger.exception("Falha no ciclo periodico do scheduler")


@app.on_event("startup")
def startup_scheduler() -> None:
    global scheduler_thread
    ensure_estab_config_table()
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
    try:
        with scheduler_lock:
            return _run_extraction_cycle(estabelecimento=estabelecimento)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=friendly_oracle_error(exc))


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
    try:
        return consult_note_by_nr_sequencia(
            estabelecimento=estabelecimento,
            nr_sequencia=nr_sequencia,
            db_client=oracle_client,
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail=friendly_oracle_error(exc))


@app.post("/notas/marcar-integrada")
def marcar_nota_integrada(nr_sequencia: str) -> dict:
    """Atualiza dt_integracao = SYSDATE no Tasy apos sucesso no PR."""
    if not str(nr_sequencia).strip():
        raise HTTPException(status_code=422, detail="nr_sequencia obrigatorio")
    oracle_client = MockOracleClient() if USE_MOCK_ORACLE else None
    try:
        return mark_note_integrated(nr_sequencia=nr_sequencia, db_client=oracle_client)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=friendly_oracle_error(exc))


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
    except Exception as exc:
        raise HTTPException(status_code=503, detail=friendly_oracle_error(exc))
    publish_raw_note(note.model_dump(mode="json"))
    return {
        "estabelecimento": estabelecimento,
        "nr_sequencia": nr_sequencia,
        "nf": note.nf,
        "published": True,
    }
