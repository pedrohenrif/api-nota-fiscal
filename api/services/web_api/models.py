from sqlalchemy import Column, DateTime, Integer, String, Text, func

from services.web_api.db import Base


class Usuario(Base):
    __tablename__ = "usuario"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(80), nullable=False, unique=True, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="usuario")
    estabelecimento = Column(String(80), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AccessAuditLog(Base):
    """Registro de acesso e acoes do painel (IP, usuario, endpoint)."""

    __tablename__ = "access_audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    username = Column(String(80), nullable=True, index=True)
    role = Column(String(20), nullable=True)
    estabelecimento = Column(String(80), nullable=True)
    ip = Column(String(80), nullable=False, index=True)
    method = Column(String(10), nullable=False)
    path = Column(String(255), nullable=False)
    action = Column(String(80), nullable=False, index=True)
    status_code = Column(Integer, nullable=False)
    detail = Column(Text, nullable=True)
    user_agent = Column(String(255), nullable=True)
