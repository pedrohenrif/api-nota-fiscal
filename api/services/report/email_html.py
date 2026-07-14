from __future__ import annotations

from datetime import datetime
from typing import Any


def _fmt_money(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    formatted = f"{number:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {formatted}"


def _table(headers: list[str], rows: list[list[str]]) -> str:
    head = "".join(
        f"<th style='padding:10px 12px;text-align:left;background:#0f4c5c;color:#fff;"
        f"font-size:13px;border:1px solid #0c3a46;'>{h}</th>"
        for h in headers
    )
    body_rows = []
    for i, row in enumerate(rows):
        bg = "#f7fafb" if i % 2 == 0 else "#ffffff"
        cells = "".join(
            f"<td style='padding:9px 12px;border:1px solid #e2e8f0;font-size:13px;"
            f"color:#1a202c;background:{bg};'>{cell}</td>"
            for cell in row
        )
        body_rows.append(f"<tr>{cells}</tr>")
    return (
        "<table style='border-collapse:collapse;width:100%;margin:0 0 20px;"
        "font-family:Segoe UI,Arial,sans-serif;'>"
        f"<thead><tr>{head}</tr></thead>"
        f"<tbody>{''.join(body_rows)}</tbody></table>"
    )


def _section(title: str, accent: str, headers: list[str], rows: list[list[str]]) -> str:
    if not rows:
        return ""
    return (
        f"<h3 style='margin:28px 0 10px;font-family:Segoe UI,Arial,sans-serif;"
        f"color:{accent};font-size:16px;border-left:4px solid {accent};padding-left:10px;'>"
        f"{title} <span style='color:#64748b;font-weight:500;'>({len(rows)})</span></h3>"
        f"{_table(headers, rows)}"
    )


def build_report_html(
    estabelecimento: str,
    *,
    integradas: list[dict[str, Any]],
    nao_integradas: list[dict[str, Any]],
    sem_depara: list[dict[str, Any]],
    sem_lote: list[dict[str, Any]],
    erros_pr: list[dict[str, Any]],
) -> str:
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")
    summary = (
        f"{len(integradas)} integradas · {len(nao_integradas)} nao integradas · "
        f"{len(sem_depara)} sem de-para · {len(sem_lote)} sem lote · {len(erros_pr)} erros PR"
    )

    integ_rows = [
        [
            str(n.get("nr_sequencia", "")),
            str(n.get("nf", "")),
            _fmt_money(n.get("valor_total")),
            str(n.get("pr_id") or "—"),
        ]
        for n in integradas
    ]
    nao_rows = [
        [
            str(n.get("nr_sequencia", "")),
            str(n.get("nf", "")),
            _fmt_money(n.get("valor_total")),
        ]
        for n in nao_integradas
    ]
    depara_rows = [
        [
            str(n.get("nr_sequencia", "")),
            str(n.get("nf", "")),
            _fmt_money(n.get("valor_total")),
            "<br>".join(str(i) for i in n.get("itens", [])),
            "<br>".join(str(d) for d in n.get("descricoes", [])),
        ]
        for n in sem_depara
    ]
    lote_rows = [
        [
            str(n.get("nr_sequencia", "")),
            str(n.get("nf", "")),
            str(n.get("inconsistencia", "")),
        ]
        for n in sem_lote
    ]
    erro_rows = [
        [
            str(n.get("nr_sequencia", "")),
            str(n.get("nf", "")),
            str(n.get("status", "")),
            str(n.get("erro", ""))[:300],
        ]
        for n in erros_pr
    ]

    sections = "".join(
        [
            _section(
                "Notas integradas",
                "#15803d",
                ["Numero Tasy", "Numero NF", "Valor", "ID PR"],
                integ_rows,
            ),
            _section(
                "Notas nao integradas",
                "#b45309",
                ["Numero Tasy", "Numero NF", "Valor"],
                nao_rows,
            ),
            _section(
                "Notas com item sem de-para",
                "#b91c1c",
                ["Numero Tasy", "Numero NF", "Valor", "Item", "Descricao"],
                depara_rows,
            ),
            _section(
                "Itens com necessidade de lote",
                "#7c3aed",
                ["Numero Tasy", "Numero NF", "Inconsistencia"],
                lote_rows,
            ),
            _section(
                "Erros de retorno do PR",
                "#dc2626",
                ["Numero Tasy", "Numero NF", "Status", "Erro"],
                erro_rows,
            ),
        ]
    )

    if not sections:
        sections = (
            "<p style='font-family:Segoe UI,Arial,sans-serif;color:#64748b;'>"
            "Nenhuma ocorrencia no periodo.</p>"
        )

    return f"""
<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#eef2f7;">
  <div style="max-width:900px;margin:24px auto;background:#fff;border-radius:12px;
              overflow:hidden;border:1px solid #dbe3ee;">
    <div style="background:linear-gradient(120deg,#0f4c5c,#1b6b7a);color:#fff;padding:22px 24px;">
      <div style="font-family:Segoe UI,Arial,sans-serif;font-size:12px;opacity:.85;">
        Relatorio operacional ISMS
      </div>
      <h1 style="margin:6px 0 0;font-family:Segoe UI,Arial,sans-serif;font-size:22px;">
        Notas Fiscais — {estabelecimento}
      </h1>
      <div style="margin-top:8px;font-family:Segoe UI,Arial,sans-serif;font-size:13px;opacity:.9;">
        {agora}
      </div>
    </div>
    <div style="padding:20px 24px 8px;">
      <p style="margin:0 0 8px;font-family:Segoe UI,Arial,sans-serif;color:#334155;font-size:14px;">
        <strong>Resumo:</strong> {summary}
      </p>
      {sections}
      <p style="margin:28px 0 8px;font-family:Segoe UI,Arial,sans-serif;color:#0f4c5c;">
        <strong>Atenciosamente, GHR Tech</strong>
      </p>
    </div>
  </div>
</body>
</html>
"""
