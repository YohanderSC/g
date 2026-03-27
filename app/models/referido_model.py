"""
=====================================================
MODELO ORM - SOLICITUDES DE REFERIDO
=====================================================
Agregar al final de app/models/models.py
=====================================================
"""

# ── AGREGAR ESTE IMPORT AL INICIO DE models.py ──
# from sqlalchemy import Enum as SAEnum   (ya existe)

# ── AGREGAR ESTE ENUM ──────────────────────────
import enum

class EstatusReferido(str, enum.Enum):
    pendiente  = "pendiente"
    aprobado   = "aprobado"
    rechazado  = "rechazado"


# ── AGREGAR ESTA CLASE AL FINAL DE models.py ──
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func


# Copiar en models.py:
MODELO_REFERIDO = """

# ─────────────────────────────────────────────────────────
# ENUM: Estatus de solicitud de referido
# ─────────────────────────────────────────────────────────
class EstatusReferido(str, enum.Enum):
    pendiente = "pendiente"
    aprobado  = "aprobado"
    rechazado = "rechazado"


# ─────────────────────────────────────────────────────────
# MODELO: SolicitudReferido
# Registra cada vez que un cliente invita a otra persona.
# El admin aprueba o rechaza la solicitud.
# Al aprobar: se crea el cliente referido y se envía correo.
# ─────────────────────────────────────────────────────────
class SolicitudReferido(Base):
    __tablename__ = "solicitudes_referido"

    id               = Column(Integer, primary_key=True, index=True, autoincrement=True)
    referidor_id     = Column(Integer, ForeignKey("clientes.id"), nullable=False)
    email_referido   = Column(String(150), nullable=False, index=True)
    nombres_referido = Column(String(150), nullable=True)
    ruleta_id        = Column(Integer, ForeignKey("ruletas.id"), nullable=False)

    # ID del cliente creado al aprobar la solicitud
    cliente_id       = Column(Integer, ForeignKey("clientes.id"), nullable=True)

    estatus          = Column(SAEnum(EstatusReferido), default=EstatusReferido.pendiente)
    fecha_solicitud  = Column(DateTime(timezone=True), server_default=func.now())
    fecha_resolucion = Column(DateTime(timezone=True), nullable=True)

    # Relaciones
    referidor = relationship("Cliente", foreign_keys=[referidor_id])
    cliente   = relationship("Cliente", foreign_keys=[cliente_id])
    ruleta    = relationship("Ruleta")
"""
