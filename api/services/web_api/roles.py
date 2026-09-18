"""Regras de papel do painel.

Roles:
- adm: administrador global (todas as unidades, config)
- adm_local: administrador da unidade (usuarios/destinatarios/logs do estab)
- usuario: operador da unidade
- dev: operacional + auditoria de acessos e filas RabbitMQ
"""

from __future__ import annotations

from typing import Literal

RoleName = Literal["adm", "adm_local", "usuario", "dev"]

ALL_ROLES: tuple[str, ...] = ("adm", "adm_local", "usuario", "dev")
ROLES_COM_ESTABELECIMENTO = frozenset({"adm_local", "usuario"})
ROLES_SEM_ESTABELECIMENTO = frozenset({"adm", "dev"})


def is_global_admin(role: str | None) -> bool:
    return role == "adm"


def is_dev(role: str | None) -> bool:
    return role == "dev"


def is_adm_local(role: str | None) -> bool:
    return role == "adm_local"


def can_manage_users(role: str | None) -> bool:
    return role in ("adm", "adm_local")


def can_manage_config(role: str | None) -> bool:
    return role == "adm"


def can_see_acesso(role: str | None) -> bool:
    return role == "dev"


def can_see_filas(role: str | None) -> bool:
    return role == "dev"


def can_see_logs(role: str | None) -> bool:
    return role in ALL_ROLES


def requires_estabelecimento(role: str | None) -> bool:
    return role in ROLES_COM_ESTABELECIMENTO


def creatable_roles_by(actor_role: str | None) -> tuple[str, ...]:
    if actor_role == "adm":
        return ALL_ROLES
    if actor_role == "adm_local":
        return ("usuario", "adm_local")
    return ()
