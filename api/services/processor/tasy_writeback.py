from __future__ import annotations

import logging
import os

import httpx

logger = logging.getLogger(__name__)

EXTRACTOR_URL = os.getenv("EXTRACTOR_URL", "http://localhost:8001").rstrip("/")


def mark_tasy_integrated(nr_sequencia: str | None) -> dict:
    """Chama o extractor para preencher dt_integracao = SYSDATE no Oracle."""
    if not nr_sequencia or not str(nr_sequencia).strip():
        return {"updated": False, "motivo": "nr_sequencia ausente"}

    url = f"{EXTRACTOR_URL}/notas/marcar-integrada"
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, params={"nr_sequencia": str(nr_sequencia).strip()})
            if response.is_error:
                raise ValueError(f"Extractor HTTP {response.status_code}: {response.text[:500]}")
            data = response.json()
            logger.info(
                "dt_integracao atualizado no Tasy nr_sequencia=%s updated=%s",
                nr_sequencia,
                data.get("updated"),
            )
            return data
    except Exception as exc:
        logger.exception("Falha ao atualizar dt_integracao no Tasy nr_sequencia=%s", nr_sequencia)
        raise RuntimeError(f"Falha ao atualizar dt_integracao no Tasy: {exc}") from exc
