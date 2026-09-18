from __future__ import annotations

from sqlalchemy import text

from services.web_api.db import engine


def run_web_api_migrations() -> None:
    statements = [
        "ALTER TABLE usuario ADD COLUMN IF NOT EXISTS email VARCHAR(255)",
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_usuario_email_unique ON usuario (email) WHERE email IS NOT NULL",
        """
        CREATE TABLE IF NOT EXISTS password_reset_token (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255) NOT NULL,
            code_hash VARCHAR(255) NOT NULL,
            expires_at TIMESTAMPTZ NOT NULL,
            used_at TIMESTAMPTZ NULL,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
        """,
        "CREATE INDEX IF NOT EXISTS ix_password_reset_token_email ON password_reset_token (email)",
        "ALTER TABLE report_destinatario ADD COLUMN IF NOT EXISTS ativo BOOLEAN NOT NULL DEFAULT TRUE",
    ]
    with engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))
