from __future__ import annotations

import logging
import secrets

from sqlalchemy.orm import Session

from services.common.report_recipients import validate_email
from services.report.smtp_client import send_html_email
from services.web_api import repository
from services.web_api.security import hash_password, verify_password

logger = logging.getLogger(__name__)


def request_password_reset(db: Session, email: str) -> dict:
    """Sempre retorna mensagem generica (nao revela se o e-mail existe)."""
    try:
        normalized = validate_email(email)
    except ValueError:
        return {
            "ok": True,
            "mensagem": "Se o e-mail estiver cadastrado, enviaremos um codigo em instantes.",
        }

    user = repository.get_user_by_email(db, normalized)
    if user is None:
        return {
            "ok": True,
            "mensagem": "Se o e-mail estiver cadastrado, enviaremos um codigo em instantes.",
        }

    code = f"{secrets.randbelow(1_000_000):06d}"
    repository.create_password_reset_token(
        db, email=normalized, code_hash=hash_password(code), ttl_minutes=30
    )

    html = f"""
    <p>Ola, <strong>{user.username}</strong>.</p>
    <p>Use o codigo abaixo para redefinir sua senha no painel de Notas Fiscais:</p>
    <p style="font-size:28px;letter-spacing:6px;font-weight:700">{code}</p>
    <p>O codigo expira em 30 minutos. Se voce nao solicitou, ignore este e-mail.</p>
    """
    try:
        send_html_email(
            subject="Codigo para redefinir senha — Integracao NF",
            html_body=html,
            recipients=[normalized],
        )
    except Exception:
        logger.exception("Falha ao enviar e-mail de reset para %s", normalized)
        raise RuntimeError("Nao foi possivel enviar o e-mail de recuperacao agora.")

    return {
        "ok": True,
        "mensagem": "Se o e-mail estiver cadastrado, enviaremos um codigo em instantes.",
    }


def reset_password_with_code(
    db: Session, *, email: str, code: str, new_password: str
) -> dict:
    normalized = validate_email(email)
    if len(new_password) < 4:
        raise ValueError("Senha deve ter no minimo 4 caracteres")

    user = repository.get_user_by_email(db, normalized)
    token = repository.get_valid_reset_token(db, email=normalized)
    if user is None or token is None or not verify_password(code.strip(), token.code_hash):
        raise ValueError("Codigo invalido ou expirado")

    repository.set_user_password(db, user, new_password)
    repository.mark_reset_token_used(db, token)
    return {"ok": True, "mensagem": "Senha atualizada com sucesso. Voce ja pode entrar."}
