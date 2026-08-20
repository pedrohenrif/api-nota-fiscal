from threading import Event, Lock, Thread

from fastapi import FastAPI, HTTPException

from services.common.app_settings import (
    ALLOWED_REPORT_INTERVALS,
    ensure_app_settings_table,
    get_report_interval_minutes,
    set_report_interval_minutes,
)
from services.common.estabelecimentos import ESTABELECIMENTOS
from services.common.estab_config import ensure_estab_config_table, list_report_enabled
from services.common.report_recipients import ensure_report_recipients_table
from services.report.config import REPORT_SCHEDULER_ENABLED
from services.report.report_sent import ensure_report_sent_table
from services.report.service import run_report_for_estabelecimento, run_scheduled_reports

app = FastAPI(title="Report Service - E-mail NF")

scheduler_stop_signal = Event()
scheduler_lock = Lock()
scheduler_thread: Thread | None = None


@app.get("/health")
def health() -> dict:
    running = scheduler_thread.is_alive() if scheduler_thread else False
    interval = get_report_interval_minutes()
    return {
        "status": "ok",
        "service": "report",
        "scheduler_enabled": REPORT_SCHEDULER_ENABLED,
        "scheduler_running": running,
        "report_interval_minutes": interval,
        "report_interval_options": sorted(ALLOWED_REPORT_INTERVALS),
        "report_estabelecimentos": list_report_enabled() if REPORT_SCHEDULER_ENABLED else [],
    }


def _scheduler_loop() -> None:
    # Rele o intervalo a cada ciclo para refletir mudanca feita no painel.
    while True:
        interval_seconds = max(get_report_interval_minutes(), 1) * 60
        if scheduler_stop_signal.wait(timeout=interval_seconds):
            break
        with scheduler_lock:
            run_scheduled_reports()


@app.on_event("startup")
def startup() -> None:
    global scheduler_thread
    ensure_estab_config_table()
    ensure_report_sent_table()
    ensure_report_recipients_table()
    ensure_app_settings_table()
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


@app.get("/relatorios/config")
def obter_config_relatorio() -> dict:
    return {
        "report_interval_minutes": get_report_interval_minutes(),
        "report_interval_options": sorted(ALLOWED_REPORT_INTERVALS),
        "scheduler_enabled": REPORT_SCHEDULER_ENABLED,
    }


@app.patch("/relatorios/config")
def atualizar_config_relatorio(payload: dict) -> dict:
    minutes = payload.get("report_interval_minutes")
    try:
        minutes_int = int(minutes)
        value = set_report_interval_minutes(minutes_int)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "report_interval_minutes": value,
        "report_interval_options": sorted(ALLOWED_REPORT_INTERVALS),
        "scheduler_enabled": REPORT_SCHEDULER_ENABLED,
        "mensagem": (
            f"Intervalo atualizado para {value} min. "
            "Vale a partir do proximo ciclo do report-service."
        ),
    }


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
