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

# SEDE = mesmo ORACLE_DSN do extrator (fonte das notas).
ORACLE_SEDE_DSN = os.getenv("ORACLE_DSN", "")
# HRBA = destino Tasy (homolog por padrao).
ORACLE_HRBA_ENV = os.getenv("ORACLE_HRBA_ENV", "homolog").lower()
ORACLE_HRBA_DSN_HOMOLOG = os.getenv("ORACLE_HRBA_DSN_HOMOLOG", "")
ORACLE_HRBA_DSN_PRODUCTION = os.getenv("ORACLE_HRBA_DSN_PRODUCTION", "")
USE_MOCK_ORACLE = os.getenv("USE_MOCK_ORACLE", "true").lower() == "true"

CD_ESTABELECIMENTO_HRBA = int(os.getenv("HRBA_CD_ESTABELECIMENTO", "1"))
CD_NATUREZA_OPERACAO = int(os.getenv("HRBA_CD_NATUREZA_OPERACAO", "111"))
USUARIO_INTEGRACAO = os.getenv("HRBA_USUARIO_INTEGRACAO", "GHR.INTEGRACOES")
CD_ESTOQUE_DIRETO = int(os.getenv("HRBA_CD_ESTOQUE_DIRETO", "10"))
CENTRO_CUSTO_ESTOQUE_DIRETO = int(os.getenv("HRBA_CENTRO_CUSTO_ESTOQUE_DIRETO", "49"))
CENTRO_CUSTO_CONSIGNADO = int(os.getenv("HRBA_CENTRO_CUSTO_CONSIGNADO", "64"))
CD_MATERIAL_ESTOQUE = int(os.getenv("HRBA_CD_MATERIAL_ESTOQUE", "4"))

ESTABELECIMENTO_NOME = "HRBA"


def get_hrba_dsn() -> str:
    if ORACLE_HRBA_ENV == "production":
        dsn = ORACLE_HRBA_DSN_PRODUCTION.strip()
        if not dsn:
            raise ValueError("ORACLE_HRBA_DSN_PRODUCTION nao configurado")
        return dsn
    dsn = ORACLE_HRBA_DSN_HOMOLOG.strip()
    if not dsn:
        raise ValueError("ORACLE_HRBA_DSN_HOMOLOG nao configurado")
    return dsn
