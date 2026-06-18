from typing import Optional

from sqlalchemy.orm import Session

from services.web_api.models import Usuario
from services.web_api.security import hash_password


def get_user_by_username(db: Session, username: str) -> Optional[Usuario]:
    return db.query(Usuario).filter(Usuario.username == username).first()


def list_users(db: Session) -> list[Usuario]:
    return db.query(Usuario).order_by(Usuario.username).all()


def create_user(
    db: Session,
    username: str,
    password: str,
    role: str,
    estabelecimento: Optional[str],
) -> Usuario:
    user = Usuario(
        username=username,
        hashed_password=hash_password(password),
        role=role,
        estabelecimento=estabelecimento,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
