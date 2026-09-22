import os


POLL_INTERVAL_MINUTES = int(os.getenv("POLL_INTERVAL_MINUTES", "6"))
EXTRACTION_SCHEDULER_ENABLED = (
    os.getenv("EXTRACTION_SCHEDULER_ENABLED", "true").lower() == "true"
)
EXTRACTION_RUN_ON_STARTUP = os.getenv("EXTRACTION_RUN_ON_STARTUP", "false").lower() == "true"
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
RABBITMQ_QUEUE_RAW_NF = os.getenv("RABBITMQ_QUEUE_RAW_NF", "nf.raw")
# Scheduler nao publica se nf.raw >= este valor (evita fila explosiva quando PR esta lento).
QUEUE_BACKPRESSURE_MAX = int(os.getenv("QUEUE_BACKPRESSURE_MAX", "200"))
# true = so extrai notas com dt_emissao no mes corrente (competencia do mes).
COMPETENCIA_MES_ATUAL_ONLY = os.getenv("COMPETENCIA_MES_ATUAL_ONLY", "true").lower() in (
    "1",
    "true",
    "yes",
)
ORACLE_DSN = os.getenv("ORACLE_DSN", "")
USE_MOCK_ORACLE = os.getenv("USE_MOCK_ORACLE", "true").lower() == "true"
