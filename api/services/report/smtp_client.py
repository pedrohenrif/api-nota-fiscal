from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

from services.report.config import (
    SMTP_FROM_NAME,
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PASSWORD_FALLBACK,
    SMTP_PORT,
    SMTP_USER,
    SMTP_USER_FALLBACK,
)

logger = logging.getLogger(__name__)


def _login(server: smtplib.SMTP, user: str, password: str) -> None:
    server.login(user, password)


def send_html_email(*, subject: str, html_body: str, recipients: list[str]) -> dict:
    if not recipients:
        raise ValueError("Lista de destinatarios vazia")

    accounts: list[tuple[str, str]] = []
    if SMTP_USER and SMTP_PASSWORD:
        accounts.append((SMTP_USER, SMTP_PASSWORD))
    if SMTP_USER_FALLBACK and SMTP_PASSWORD_FALLBACK:
        accounts.append((SMTP_USER_FALLBACK, SMTP_PASSWORD_FALLBACK))
    if not accounts:
        raise ValueError("SMTP_USER/SMTP_PASSWORD nao configurados no .env")

    last_error: Exception | None = None
    for user, password in accounts:
        server: smtplib.SMTP | None = None
        try:
            logger.info("Conectando SMTP %s:%s como %s", SMTP_HOST, SMTP_PORT, user)
            server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30)
            server.starttls()
            _login(server, user, password)

            message = MIMEMultipart()
            message["From"] = formataddr((SMTP_FROM_NAME, user))
            message["To"] = ", ".join(recipients)
            message["Subject"] = subject
            message.attach(MIMEText(html_body, "html", "utf-8"))

            server.sendmail(user, recipients, message.as_string())
            logger.info("E-mail enviado para: %s", ", ".join(recipients))
            return {"enviado": True, "remetente": user, "destinatarios": recipients}
        except Exception as exc:  # pragma: no cover
            last_error = exc
            logger.warning("Falha SMTP com %s: %s", user, exc)
        finally:
            if server is not None:
                try:
                    server.quit()
                except Exception:
                    pass

    raise RuntimeError(f"Falha ao enviar e-mail: {last_error}")
