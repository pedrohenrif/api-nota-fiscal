from __future__ import annotations

from datetime import datetime
from typing import Any

from services.common.estab_config import list_report_enabled
from services.report.classifier import classify_estabelecimento, has_report_content
from services.report.config import get_recipients
from services.report.email_html import build_report_html
from services.report.report_sent import ensure_report_sent_table, mark_report_sent
from services.report.smtp_client import send_html_email


def run_report_for_estabelecimento(
    estabelecimento: str,
    *,
    force_send: bool = False,
) -> dict[str, Any]:
    ensure_report_sent_table()
    report = classify_estabelecimento(estabelecimento)
    recipients = get_recipients(estabelecimento)

    if not recipients:
        return {
            "estabelecimento": estabelecimento,
            "enviado": False,
            "motivo": "Sem destinatarios configurados no .env (REPORT_EMAIL_*)",
            "totais": report["totais"],
        }

    if not force_send and not has_report_content(report):
        return {
            "estabelecimento": estabelecimento,
            "enviado": False,
            "motivo": "Nenhuma ocorrencia no periodo",
            "totais": report["totais"],
        }

    html = build_report_html(
        estabelecimento,
        integradas=report["integradas"],
        nao_integradas=report["nao_integradas"],
        sem_depara=report["sem_depara"],
        sem_lote=report["sem_lote"],
        erros_pr=report["erros_pr"],
    )
    subject = (
        f"Notas Fiscais ISMS - {estabelecimento} - "
        f"{datetime.now().strftime('%d/%m/%Y %H:%M')}"
    )
    send_result = send_html_email(
        subject=subject, html_body=html, recipients=recipients
    )
    marcados = mark_report_sent(estabelecimento, report)
    return {
        "estabelecimento": estabelecimento,
        "enviado": True,
        "totais": report["totais"],
        "marcados_envio_unico": marcados,
        "destinatarios": send_result["destinatarios"],
        "remetente": send_result["remetente"],
    }


def run_scheduled_reports() -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for estabelecimento in list_report_enabled():
        try:
            results.append(run_report_for_estabelecimento(estabelecimento, force_send=False))
        except Exception as exc:  # pragma: no cover
            results.append(
                {
                    "estabelecimento": estabelecimento,
                    "enviado": False,
                    "motivo": str(exc),
                }
            )
    return results
