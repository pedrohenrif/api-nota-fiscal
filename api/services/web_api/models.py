from sqlalchemy import Column, DateTime, Integer, String, func

from services.web_api.db import Base


class Usuario(Base):
    __tablename__ = "usuario"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(80), nullable=False, unique=True, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="usuario")
    estabelecimento = Column(String(80), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
