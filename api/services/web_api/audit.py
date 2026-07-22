from __future__ import annotations

from typing import Any, Optional

from fastapi import Request
from sqlalchemy.orm import Session

from services.web_api.models import AccessAuditLog
from services.web_api.security import decode_access_token

# Paths que nao geram ruido no audit.
_SKIP_PREFIXES = ("/health", "/docs", "/openapi.json", "/redoc")

_ACTION_MAP: list[tuple[str, str, str]] = [
    ("POST", "/auth/login", "login"),
    ("GET", "/auth/me", "sessao"),
    ("GET", "/notas", "listar_notas"),
    ("POST", "/notas/emitir", "emitir_pendentes"),
    ("POST", "/notas/emitir-especifica", "emitir_especifica"),
    ("POST", "/notas/reemitir", "reemitir_nota"),
    ("GET", "/notas/", "detalhe_nota"),
    ("GET", "/admin/logs", "listar_logs_processamento"),
    ("GET", "/admin/acesso", "listar_acesso"),
    ("GET", "/admin/estabelecimentos/config", "listar_config"),
    ("PATCH", "/admin/estabelecimentos/", "atualizar_config"),
    ("POST", "/admin/relatorios/enviar", "enviar_relatorio"),
    ("GET", "/usuarios", "listar_usuarios"),
    ("POST", "/usuarios", "criar_usuario"),
    ("GET", "/estabelecimentos", "listar_estabelecimentos"),
]


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()[:80]
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()[:80]
    if request.client and request.client.host:
        return request.client.host[:80]
    return "unknown"


def resolve_action(method: str, path: str) -> str:
    for m, prefix, action in _ACTION_MAP:
        if method == m and (path == prefix or path.startswith(prefix)):
            return action
    return f"{method.lower()}_{path.strip('/').replace('/', '_') or 'root'}"[:80]


def username_from_request(request: Request) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """Retorna (username, role, estabelecimento) a partir do Bearer, se houver."""
    auth = request.headers.get("authorization") or ""
    if not auth.lower().startswith("bearer "):
        return None, None, None
    token = auth.split(" ", 1)[1].strip()
    if not token:
        return None, None, None
    try:
        payload = decode_access_token(token)
    except Exception:
        return None, None, None
    return (
        (payload.get("sub") or None),
        (payload.get("role") or None),
        (payload.get("estabelecimento") or None),
    )


def should_skip_path(path: str) -> bool:
    return any(path == p or path.startswith(p + "/") for p in _SKIP_PREFIXES)


def write_audit_log(
    db: Session,
    *,
    ip: str,
    method: str,
    path: str,
    status_code: int,
    username: Optional[str] = None,
    role: Optional[str] = None,
    estabelecimento: Optional[str] = None,
    action: Optional[str] = None,
    detail: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> None:
    db.add(
        AccessAuditLog(
            username=username,
            role=role,
            estabelecimento=estabelecimento,
            ip=ip,
            method=method[:10],
            path=path[:255],
            action=action or resolve_action(method, path),
            status_code=status_code,
            detail=(detail[:2000] if detail else None),
            user_agent=(user_agent[:255] if user_agent else None),
        )
    )
    db.commit()


def list_access_logs(
    db: Session,
    *,
    username: Optional[str] = None,
    ip: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> dict[str, Any]:
    from sqlalchemy import func

    query = db.query(AccessAuditLog)
    if username:
        query = query.filter(AccessAuditLog.username.ilike(f"%{username.strip()}%"))
    if ip:
        query = query.filter(AccessAuditLog.ip.ilike(f"%{ip.strip()}%"))
    if action:
        query = query.filter(AccessAuditLog.action == action.strip())

    total = query.with_entities(func.count(AccessAuditLog.id)).scalar() or 0
    rows = (
        query.order_by(AccessAuditLog.created_at.desc(), AccessAuditLog.id.desc())
        .offset(max(offset, 0))
        .limit(min(max(limit, 1), 500))
        .all()
    )
    return {
        "total": int(total),
        "limit": min(max(limit, 1), 500),
        "offset": max(offset, 0),
        "items": [
            {
                "id": row.id,
                "created_at": row.created_at,
                "username": row.username,
                "role": row.role,
                "estabelecimento": row.estabelecimento,
                "ip": row.ip,
                "method": row.method,
                "path": row.path,
                "action": row.action,
                "status_code": row.status_code,
                "detail": row.detail,
                "user_agent": row.user_agent,
            }
            for row in rows
        ],
    }
