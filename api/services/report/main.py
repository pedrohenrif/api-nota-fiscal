from threading import Event, Lock, Thread

from fastapi import FastAPI, HTTPException

from services.common.estabelecimentos import ESTABELECIMENTOS
from services.common.estab_config import ensure_estab_config_table, list_report_enabled
from services.report.config import REPORT_INTERVAL_MINUTES, REPORT_SCHEDULER_ENABLED
from services.report.service import run_report_for_estabelecimento, run_scheduled_reports

app = FastAPI(title="Report Service - E-mail NF")

scheduler_stop_signal = Event()
scheduler_lock = Lock()
scheduler_thread: Thread | None = None


@app.get("/health")
def health() -> dict:
    running = scheduler_thread.is_alive() if scheduler_thread else False
    return {
        "status": "ok",
        "service": "report",
        "scheduler_enabled": REPORT_SCHEDULER_ENABLED,
        "scheduler_running": running,
        "report_interval_minutes": REPORT_INTERVAL_MINUTES,
        "report_estabelecimentos": list_report_enabled() if REPORT_SCHEDULER_ENABLED else [],
    }


def _scheduler_loop() -> None:
    interval_seconds = max(REPORT_INTERVAL_MINUTES, 1) * 60
    while not scheduler_stop_signal.wait(timeout=interval_seconds):
        if scheduler_stop_signal.is_set():
            break
        with scheduler_lock:
            run_scheduled_reports()


@app.on_event("startup")
def startup() -> None:
    global scheduler_thread
    ensure_estab_config_table()
    if not REPORT_SCHEDULER_ENABLED:
        return
    if scheduler_thread and scheduler_thread.is_alive():
        return
    scheduler_stop_signal.clear()
    scheduler_thread = Thread(
        target=_scheduler_loop,
        daemon=True,
        name="report-scheduler-worker",
    )
    scheduler_thread.start()


@app.on_event("shutdown")
def shutdown() -> None:
    scheduler_stop_signal.set()


@app.post("/relatorios/enviar")
def enviar_relatorio(estabelecimento: str) -> dict:
    if estabelecimento not in ESTABELECIMENTOS:
        raise HTTPException(status_code=422, detail="Estabelecimento invalido")
    try:
        with scheduler_lock:
            return run_report_for_estabelecimento(estabelecimento, force_send=True)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/relatorios/ciclo")
def ciclo_relatorios() -> dict:
    with scheduler_lock:
        resultados = run_scheduled_reports()
    return {"resultados": resultados}
