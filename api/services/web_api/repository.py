from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from services.web_api.models import PasswordResetToken, Usuario
from services.web_api.security import hash_password


def get_user_by_username(db: Session, username: str) -> Optional[Usuario]:
    return db.query(Usuario).filter(Usuario.username == username).first()


def get_user_by_email(db: Session, email: str) -> Optional[Usuario]:
    normalized = (email or "").strip().lower()
    if not normalized:
        return None
    return db.query(Usuario).filter(Usuario.email == normalized).first()


def list_users(
    db: Session,
    *,
    estabelecimento: Optional[str] = None,
) -> list[Usuario]:
    query = db.query(Usuario)
    if estabelecimento:
        query = query.filter(Usuario.estabelecimento == estabelecimento)
    return query.order_by(Usuario.username).all()


def create_user(
    db: Session,
    username: str,
    password: str,
    role: str,
    estabelecimento: Optional[str],
    email: Optional[str] = None,
) -> Usuario:
    user = Usuario(
        username=username,
        email=(email or "").strip().lower() or None,
        hashed_password=hash_password(password),
        role=role,
        estabelecimento=estabelecimento,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user_by_id(db: Session, user_id: int) -> Optional[Usuario]:
    return db.query(Usuario).filter(Usuario.id == user_id).first()


def update_user_email(
    db: Session, user: Usuario, email: Optional[str]
) -> Usuario:
    user.email = (email or "").strip().lower() or None
    db.commit()
    db.refresh(user)
    return user


def set_user_password(db: Session, user: Usuario, password: str) -> Usuario:
    user.hashed_password = hash_password(password)
    db.commit()
    db.refresh(user)
    return user


def create_password_reset_token(
    db: Session,
    *,
    email: str,
    code_hash: str,
    ttl_minutes: int = 30,
) -> PasswordResetToken:
    token = PasswordResetToken(
        email=email.strip().lower(),
        code_hash=code_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes),
    )
    db.add(token)
    db.commit()
    db.refresh(token)
    return token


def get_valid_reset_token(
    db: Session, *, email: str
) -> Optional[PasswordResetToken]:
    now = datetime.now(timezone.utc)
    return (
        db.query(PasswordResetToken)
        .filter(
            PasswordResetToken.email == email.strip().lower(),
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.expires_at >= now,
        )
        .order_by(PasswordResetToken.id.desc())
        .first()
    )


def mark_reset_token_used(db: Session, token: PasswordResetToken) -> None:
    token.used_at = datetime.now(timezone.utc)
    db.commit()
