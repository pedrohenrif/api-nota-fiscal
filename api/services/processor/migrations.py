from datetime import datetime

from sqlalchemy import text

from services.processor.db import engine


def run_migrations() -> None:
    statements = [
        "ALTER TABLE nota_processamento ADD COLUMN IF NOT EXISTS nr_sequencia VARCHAR(80)",
        "ALTER TABLE nota_processamento ADD COLUMN IF NOT EXISTS fornecedor VARCHAR(20)",
        "ALTER TABLE nota_processamento ADD COLUMN IF NOT EXISTS data_nf TIMESTAMPTZ",
    ]
    with engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))


def parse_payload_metadata(payload: dict) -> tuple[str | None, str | None, datetime | None]:
    fornecedor_data = payload.get("fornecedor")
    fornecedor = None
    if isinstance(fornecedor_data, dict):
        fornecedor = fornecedor_data.get("cnpj")

    nr_sequencia = payload.get("nrSequencia")
    if nr_sequencia is not None:
        nr_sequencia = str(nr_sequencia)

    data_nf_raw = payload.get("dataNF")
    data_nf = None
    if isinstance(data_nf_raw, datetime):
        data_nf = data_nf_raw
    elif isinstance(data_nf_raw, str) and data_nf_raw:
        try:
            data_nf = datetime.fromisoformat(data_nf_raw.replace("Z", "+00:00"))
        except ValueError:
            data_nf = None

    return nr_sequencia, fornecedor, data_nf
