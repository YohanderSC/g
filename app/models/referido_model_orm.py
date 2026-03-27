"""
=====================================================
MODELO ORM - SOLICITUD DE REFERIDO
=====================================================
Archivo separado para evitar imports circulares.
Se importa en main.py para que SQLAlchemy cree la tabla.
=====================================================
"""
import enum
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.database import Base


class EstatusReferido(str, enum.Enum):
    pendiente = "pendiente"
    aprobado  = "aprobado"
    rechazado = "rechazado"


class SolicitudReferido(Base):
    __tablename__ = "solicitudes_referido"

    id               = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # El cliente que hace la referencia
    referidor_id     = Column(Integer, ForeignKey("clientes.id"), nullable=False)

    # Datos del invitado (aún no es cliente)
    email_referido   = Column(String(150), nullable=False, index=True)
    nombres_referido = Column(String(150), nullable=True)

    # Ruleta en la que participará el referido
    ruleta_id        = Column(Integer, ForeignKey("ruletas.id"), nullable=False)

    # Una vez aprobado, apunta al cliente creado
    cliente_id       = Column(Integer, ForeignKey("clientes.id"), nullable=True)

    estatus          = Column(SAEnum(EstatusReferido), default=EstatusReferido.pendiente, nullable=False)
    fecha_solicitud  = Column(DateTime(timezone=True), server_default=func.now())
    fecha_resolucion = Column(DateTime(timezone=True), nullable=True)

    # Relaciones
    referidor = relationship("Cliente", foreign_keys=[referidor_id], lazy="joined")
    cliente   = relationship("Cliente", foreign_keys=[cliente_id])
    ruleta    = relationship("Ruleta",  foreign_keys=[ruleta_id])
