from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import bcrypt
import jwt

from services.web_api.config import JWT_ALGORITHM, JWT_EXPIRE_MINUTES, JWT_SECRET

# bcrypt opera sobre no maximo 72 bytes; truncamos de forma explicita e estavel.
_BCRYPT_MAX_BYTES = 72


def _encode_secret(password: str) -> bytes:
    return password.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(password: str) -> str:
    hashed = bcrypt.hashpw(_encode_secret(password), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            _encode_secret(plain_password), hashed_password.encode("utf-8")
        )
    except ValueError:
        return False


def create_access_token(subject: str, role: str, estabelecimento: Optional[str]) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE_MINUTES)
    payload: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "estabelecimento": estabelecimento,
        "exp": expire,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
