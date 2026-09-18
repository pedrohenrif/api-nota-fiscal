from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from services.web_api.db import get_db
from services.web_api.models import Usuario
from services.web_api.repository import get_user_by_username
from services.web_api.roles import (
    can_manage_config,
    can_manage_users,
    can_see_acesso,
    is_global_admin,
)
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
    if not is_global_admin(current_user.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a administradores globais",
        )
    return current_user


def require_user_manager(current_user: Usuario = Depends(get_current_user)) -> Usuario:
    if not can_manage_users(current_user.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a administradores de usuarios",
        )
    return current_user


def require_config_admin(current_user: Usuario = Depends(get_current_user)) -> Usuario:
    if not can_manage_config(current_user.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a administradores globais",
        )
    return current_user


def require_dev(current_user: Usuario = Depends(get_current_user)) -> Usuario:
    if not can_see_acesso(current_user.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito ao perfil dev",
        )
    return current_user
