import os

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
RABBITMQ_QUEUE_RAW_NF = os.getenv("RABBITMQ_QUEUE_RAW_NF", "nf.raw")
RABBITMQ_QUEUE_DEAD = os.getenv("RABBITMQ_QUEUE_DEAD", "nf.dead")
CONSUMER_IDLE_SLEEP_SECONDS = float(os.getenv("CONSUMER_IDLE_SLEEP_SECONDS", "2"))
RETRY_DELAY_SECONDS = int(os.getenv("RETRY_DELAY_SECONDS", "10"))
MAX_PROCESSING_RETRIES = int(os.getenv("MAX_PROCESSING_RETRIES", "3"))
POSTGRES_URL = os.getenv("POSTGRES_URL", "postgresql://tasy:tasy@localhost:5432/tasy_db")

# homolog | production
PR_ENV = os.getenv("PR_ENV", "homolog").lower()

PR_BASE_URL_HOMOLOG = os.getenv(
    "PR_BASE_URL_HOMOLOG", "http://prsistemas.ddns.net:6728/PREstAPI"
)
PR_BASE_URL_PRODUCTION = os.getenv(
    "PR_BASE_URL_PRODUCTION", "http://131.72.96.43:4780/PREstAPI"
)

PR_HOMOLOG_TOKEN = os.getenv(
    "PR_HOMOLOG_TOKEN", "42F6A807-AB4E-4C86-AF66-BDB5BDA045F0"
)

PR_PRODUCTION_TOKENS = {
    "Castelo": os.getenv("PR_CASTELO_TOKEN", "9EEAD5CE-639D-43BF-83AB-48116F51A41B"),
    "HRAS": os.getenv("PR_HRAS_TOKEN", "8910D4E2-731E-45CF-BE43-F9D47209487E"),
    "HRT": os.getenv("PR_HRT_TOKEN", "4936C942-ACAF-478A-9ADB-86BE99FE4576"),
    "Ponta Pora": os.getenv("PR_PONTA_PORA_TOKEN", "AD594FE2-5A81-4444-A8F3-D3BD8BBD6529"),
}

PR_NF_PATH = "/NF"
PR_PRODUTO_DEPARA_PATH = "/Controle/produtos/{cod_vinculo}"


def get_pr_config(estabelecimento: str) -> dict[str, str]:
    if PR_ENV == "production":
        token = PR_PRODUCTION_TOKENS.get(estabelecimento, "")
        if not token:
            raise ValueError(f"Token de producao ausente para: {estabelecimento}")
        return {"base_url": PR_BASE_URL_PRODUCTION.rstrip("/"), "token": token}

    if not PR_HOMOLOG_TOKEN:
        raise ValueError("Token de homologacao ausente (PR_HOMOLOG_TOKEN)")
    return {"base_url": PR_BASE_URL_HOMOLOG.rstrip("/"), "token": PR_HOMOLOG_TOKEN}
