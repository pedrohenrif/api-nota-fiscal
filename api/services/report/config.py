import os

from services.common.estabelecimentos import ESTABELECIMENTOS

REPORT_INTERVAL_MINUTES = int(os.getenv("REPORT_INTERVAL_MINUTES", "30"))
REPORT_SCHEDULER_ENABLED = os.getenv("REPORT_SCHEDULER_ENABLED", "true").lower() == "true"
REPORT_LOOKBACK_MINUTES = int(os.getenv("REPORT_LOOKBACK_MINUTES", "30"))
USE_MOCK_ORACLE = os.getenv("USE_MOCK_ORACLE", "true").lower() == "true"

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "API GHR")
SMTP_USER_FALLBACK = os.getenv("SMTP_USER_FALLBACK", "")
SMTP_PASSWORD_FALLBACK = os.getenv("SMTP_PASSWORD_FALLBACK", "")

_EMAIL_ENV_KEYS = {
    "Castelo": "REPORT_EMAIL_CASTELO",
    "HRAS": "REPORT_EMAIL_HRAS",
    "HRT": "REPORT_EMAIL_HRT",
    "Ponta Pora": "REPORT_EMAIL_PONTA_PORA",
}


def get_recipients(estabelecimento: str) -> list[str]:
    env_key = _EMAIL_ENV_KEYS.get(estabelecimento)
    if not env_key:
        return []
    raw = os.getenv(env_key, "")
    return [part.strip() for part in raw.split(",") if part.strip()]


def list_estabelecimentos() -> list[str]:
    return list(ESTABELECIMENTOS)
