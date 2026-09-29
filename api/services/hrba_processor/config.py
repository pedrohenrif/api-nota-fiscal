import os

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
RABBITMQ_QUEUE_HRBA_RAW = os.getenv("RABBITMQ_QUEUE_HRBA_RAW", "nf.hrba.raw")
RABBITMQ_QUEUE_HRBA_DEAD = os.getenv("RABBITMQ_QUEUE_HRBA_DEAD", "nf.hrba.dead")
CONSUMER_IDLE_SLEEP_SECONDS = float(os.getenv("CONSUMER_IDLE_SLEEP_SECONDS", "2"))
RETRY_DELAY_SECONDS = int(os.getenv("RETRY_DELAY_SECONDS", "10"))
RETRY_BACKOFF_MAX_SECONDS = int(os.getenv("RETRY_BACKOFF_MAX_SECONDS", "300"))
MAX_PROCESSING_RETRIES = int(os.getenv("MAX_PROCESSING_RETRIES", "3"))
MAX_RETRY_AGE_DAYS = float(os.getenv("MAX_RETRY_AGE_DAYS", "2"))
PUBLISH_DEAD_LETTER_QUEUE = os.getenv("PUBLISH_DEAD_LETTER_QUEUE", "false").lower() in (
    "1",
    "true",
    "yes",
)

POSTGRES_URL = os.getenv("POSTGRES_URL", "postgresql://tasy:tasy@localhost:5432/tasy_db")

from services.common.postgres_url import normalize_postgres_url

POSTGRES_URL = normalize_postgres_url(POSTGRES_URL)

USE_MOCK_ORACLE = os.getenv("USE_MOCK_ORACLE", "true").lower() == "true"

CD_ESTABELECIMENTO_HRBA = int(os.getenv("HRBA_CD_ESTABELECIMENTO", "1"))
CD_NATUREZA_OPERACAO = int(os.getenv("HRBA_CD_NATUREZA_OPERACAO", "111"))
USUARIO_INTEGRACAO = os.getenv("HRBA_USUARIO_INTEGRACAO", "GHR.INTEGRACOES")
CD_ESTOQUE_DIRETO = int(os.getenv("HRBA_CD_ESTOQUE_DIRETO", "10"))
CENTRO_CUSTO_ESTOQUE_DIRETO = int(os.getenv("HRBA_CENTRO_CUSTO_ESTOQUE_DIRETO", "49"))
CENTRO_CUSTO_CONSIGNADO = int(os.getenv("HRBA_CENTRO_CUSTO_CONSIGNADO", "64"))
CD_MATERIAL_ESTOQUE = int(os.getenv("HRBA_CD_MATERIAL_ESTOQUE", "4"))

ESTABELECIMENTO_NOME = "HRBA"

# Reexporta helpers — canal HRBA NUNCA usa ORACLE_DSN do PR.
from services.common.hrba_oracle import (  # noqa: E402
    ORACLE_HRBA_ENV,
    get_hrba_destino_dsn,
    get_hrba_sede_dsn,
)

get_hrba_dsn = get_hrba_destino_dsn
get_sede_dsn = get_hrba_sede_dsn
