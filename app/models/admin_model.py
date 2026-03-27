"""
=====================================================
MODELO ORM - ADMINISTRADORES
=====================================================
Tabla para gestionar los usuarios del panel admin.
Se crea automáticamente al iniciar la aplicación.
=====================================================
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from app.database.database import Base


class Administrador(Base):
    __tablename__ = "administradores"

    id         = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username   = Column(String(50), unique=True, index=True, nullable=False)
    email      = Column(String(150), unique=True, nullable=False)
    nombre     = Column(String(150), nullable=True)
    password_hash = Column(String(255), nullable=False)
    activo     = Column(Boolean, default=True)
    superadmin = Column(Boolean, default=False)   
    # puede crear otros admins
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    ultimo_login = Column(DateTime(timezone=True), nullable=True)
