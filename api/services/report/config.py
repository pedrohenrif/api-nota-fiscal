import os

from services.common.estabelecimentos import ESTABELECIMENTOS
from services.common.report_recipients import get_recipients as get_db_recipients

# Fallback do .env; o intervalo efetivo pode ser alterado no painel (app_setting).
REPORT_INTERVAL_MINUTES = int(os.getenv("REPORT_INTERVAL_MINUTES", "6"))
REPORT_SCHEDULER_ENABLED = os.getenv("REPORT_SCHEDULER_ENABLED", "true").lower() == "true"
# Lookback dos erros/integradas recentes no middleware (mantem >= intervalo do e-mail).
REPORT_LOOKBACK_MINUTES = int(os.getenv("REPORT_LOOKBACK_MINUTES", "30"))
USE_MOCK_ORACLE = os.getenv("USE_MOCK_ORACLE", "true").lower() == "true"

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "API GHR")
SMTP_USER_FALLBACK = os.getenv("SMTP_USER_FALLBACK", "")
SMTP_PASSWORD_FALLBACK = os.getenv("SMTP_PASSWORD_FALLBACK", "")


def get_recipients(estabelecimento: str) -> list[str]:
    return get_db_recipients(estabelecimento)


def list_estabelecimentos() -> list[str]:
    return list(ESTABELECIMENTOS)
