import os


POLL_INTERVAL_MINUTES = int(os.getenv("POLL_INTERVAL_MINUTES", "6"))
EXTRACTION_SCHEDULER_ENABLED = (
    os.getenv("EXTRACTION_SCHEDULER_ENABLED", "true").lower() == "true"
)
EXTRACTION_RUN_ON_STARTUP = os.getenv("EXTRACTION_RUN_ON_STARTUP", "false").lower() == "true"
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
RABBITMQ_QUEUE_RAW_NF = os.getenv("RABBITMQ_QUEUE_RAW_NF", "nf.raw")
ORACLE_DSN = os.getenv("ORACLE_DSN", "")
USE_MOCK_ORACLE = os.getenv("USE_MOCK_ORACLE", "true").lower() == "true"
