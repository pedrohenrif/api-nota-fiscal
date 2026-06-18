from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from services.web_api.db import get_db
from services.web_api.models import Usuario
from services.web_api.repository import get_user_by_username
from services.web_api.security import decode_access_token

_bearer = HTTPBearer(auto_error=True)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: Session = Depends(get_db),
) -> Usuario:
    invalid = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais invalidas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(credentials.credentials)
    except Exception:
        raise invalid

    username = payload.get("sub")
    if not username:
        raise invalid

    user = get_user_by_username(db, username)
    if user is None:
        raise invalid
    return user


def require_admin(current_user: Usuario = Depends(get_current_user)) -> Usuario:
    if current_user.role != "adm":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a administradores",
        )
    return current_user
