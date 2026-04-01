"""
=====================================================
MODELOS ORM - SISTEMA DE RULETA DE PREMIOS
=====================================================
Versión   : 1.1 (integración con proyecto Django heredado)

CAMBIOS RESPECTO A v1.0:
  ✅ Se agregó EstatusCliente como Enum (portado desde tabla Django)
  ✅ Se agregó PreguntaSeguridad (portado desde Django)
  ✅ Cliente enriquecido: genero, fecha_nacimiento, cargo,
       fecha_acceso, fecha_completo, pregunta_seguridad,
       respuesta_seguridad, premio FK, estatus
  ✅ Premio: existencia→cantidad_total/disponible, entregados→cantidad_entregada
  ✅ PremioCondicionado (NUEVO): reemplaza las listas hardcodeadas
       del proyecto antiguo (clientes_premios_unicos_1..4)
  ✅ La señal pre_save de Django → servicio cliente_service.py
=====================================================
"""

from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, ForeignKey,
    Text, Numeric, Enum as SAEnum, Date
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database.database import Base


# ─────────────────────────────────────────────────────────
# ENUM: Género del cliente
# Portado desde GENDER_CHOICES del modelo Django antiguo
# ─────────────────────────────────────────────────────────
class GeneroCliente(str, enum.Enum):
    masculino = "M"
    femenino  = "F"
    sin_dato  = "S"   # "Seleccione" en el sistema antiguo


# ─────────────────────────────────────────────────────────
# ENUM: Estatus del cliente en el flujo de la ruleta
# Portado desde la tabla EstatusCliente de Django.
# Se convierte a Enum para evitar tabla adicional y mantener
# la lógica del gestor de acciones (gestionar_acciones) legible.
#
#   anadido           → cliente recién importado, se le asigna token
#   registrado        → completó sus datos, se le asigna premio
#   participo         → giró la ruleta, se le envía felicitación
#   referido          → fue invitado por otro cliente
#   referido_aprobado → aprobado, se le envía invitación
#   referido_rechazado→ solicitud de referido rechazada
# ─────────────────────────────────────────────────────────
class EstatusCliente(str, enum.Enum):
    anadido             = "anadido"
    registrado          = "registrado"
    participo           = "participo"
    referido            = "referido"
    referido_aprobado   = "referido_aprobado"
    referido_rechazado  = "referido_rechazado"


# ─────────────────────────────────────────────────────────
# ENUM: Estado de envío de correo
# ─────────────────────────────────────────────────────────
class EstadoCorreo(str, enum.Enum):
    pendiente = "pendiente"
    enviado   = "enviado"
    fallido   = "fallido"
    reenviado = "reenviado"


# ─────────────────────────────────────────────────────────
# ENUM: Tipo de correo enviado al cliente
# ─────────────────────────────────────────────────────────
class TipoCorreo(str, enum.Enum):
    invitacion   = "invitacion"
    felicitacion = "felicitacion"
    referido     = "referido"
    reenvio      = "reenvio"


# ─────────────────────────────────────────────────────────
# MODELO: PreguntaSeguridad
# Portado del proyecto Django. Preguntas de seguridad
# opcionales para validar identidad del cliente.
# ─────────────────────────────────────────────────────────
class PreguntaSeguridad(Base):
    __tablename__ = "preguntas_seguridad"

    id       = Column(Integer, primary_key=True, index=True, autoincrement=True)
    pregunta = Column(Text, nullable=False)
    activa   = Column(Boolean, default=True)   # Campo nuevo: permite desactivar preguntas

    clientes = relationship("Cliente", back_populates="pregunta_seguridad")


# ─────────────────────────────────────────────────────────
# MODELO: Agencia
# Portado y enriquecido desde el proyecto Django.
# Nuevo: ciudad, direccion, activa, timestamps
# ─────────────────────────────────────────────────────────
class Agencia(Base):
    __tablename__ = "agencias"

    id          = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nombre      = Column(String(150), nullable=False)
    descripcion = Column(Text, nullable=True)            # Portado del modelo antiguo
    ciudad      = Column(String(100), nullable=True)     # Nuevo
    direccion   = Column(String(255), nullable=True)     # Nuevo
    activa      = Column(Boolean, default=True)          # Nuevo
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    updated_at  = Column(DateTime(timezone=True), onupdate=func.now())

    clientes = relationship("Cliente", back_populates="agencia")


# ─────────────────────────────────────────────────────────
# MODELO: Ruleta
# Portado y enriquecido desde el proyecto Django.
# Cambio: DateField → DateTime para registrar hora exacta
# Nuevo: activa, max_giros, timestamps
# ─────────────────────────────────────────────────────────
class Ruleta(Base):
    __tablename__ = "ruletas"

    id           = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nombre       = Column(String(150), nullable=False)
    descripcion  = Column(Text, nullable=True)
    # Antiguo: DateField (solo fecha). Ahora: DateTime (fecha + hora exacta de inicio/cierre)
    fecha_inicio = Column(DateTime(timezone=True), nullable=False)
    fecha_cierre = Column(DateTime(timezone=True), nullable=True)
    activa       = Column(Boolean, default=True)
    max_giros    = Column(Integer, default=1)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())
    updated_at   = Column(DateTime(timezone=True), onupdate=func.now())
    #Temas de la ruleta
    tema         = Column(String(50),  nullable=True, default='default')
    tema_imagen  = Column(String(500), nullable=True)
    tema_color1  = Column(String(7),   nullable=True)
    tema_color2  = Column(String(7),   nullable=True)
    tema_color3  = Column(String(7),   nullable=True)

    premios         = relationship("Premio", back_populates="ruleta")
    participaciones = relationship("Participacion", back_populates="ruleta")


# ─────────────────────────────────────────────────────────
# MODELO: Premio
# Portado y enriquecido desde el proyecto Django.
#
# CAMBIOS DE NOMENCLATURA (mantiene compatibilidad semántica):
#   existencia  → cantidad_total (total en stock)
#               + cantidad_disponible (aún por asignar)
#   entregados  → cantidad_entregada
#
# NUEVO: porcentaje_prob, imagen_url, es_condicionado, timestamps
# ─────────────────────────────────────────────────────────
class Premio(Base):
    __tablename__ = "premios"

    id                  = Column(Integer, primary_key=True, index=True, autoincrement=True)
    ruleta_id           = Column(Integer, ForeignKey("ruletas.id"), nullable=False)
    nombre              = Column(String(150), nullable=False)

    # Portado (renombrado): existencia del sistema antiguo
    cantidad_total      = Column(Integer, nullable=False, default=0)
    cantidad_disponible = Column(Integer, nullable=False, default=0)
    # Portado (renombrado): entregados del sistema antiguo
    cantidad_entregada  = Column(Integer, default=0)

    # Nuevos campos
    porcentaje_prob  = Column(Numeric(5, 2), default=0.00)  # Probabilidad de ganar (%)
    imagen_url       = Column(String(255), nullable=True)
    # es_condicionado reemplaza las listas hardcodeadas del proyecto antiguo
    # (premios_unicos_1..4 y clientes_condicionados)
    es_condicionado  = Column(Boolean, default=False)
    created_at       = Column(DateTime(timezone=True), server_default=func.now())
    updated_at       = Column(DateTime(timezone=True), onupdate=func.now())

    ruleta          = relationship("Ruleta", back_populates="premios")
    participaciones = relationship("Participacion", back_populates="premio")
    clientes        = relationship("Cliente", back_populates="premio")
    condicionados   = relationship("PremioCondicionado", back_populates="premio")


# ─────────────────────────────────────────────────────────
# MODELO: PremioCondicionado  ← NUEVO (no existía en el proyecto Django)
# Reemplaza las listas hardcodeadas del código antiguo:
#   clientes_premios_unicos_1 = []   → ahora es una fila en esta tabla
#   clientes_premios_unicos_2 = []
#   clientes_premios_unicos_3 = []
#   clientes_premios_unicos_4 = []
#
# Ejemplo de lo que antes era:
#   premios_unicos_1 = [1]
#   clientes_premios_unicos_1 = ["giovanni.cristaldo@prana.com.py"]
# Ahora se registra en BD y se puede gestionar desde la API
# ─────────────────────────────────────────────────────────
class PremioCondicionado(Base):
    __tablename__ = "premios_condicionados"

    id            = Column(Integer, primary_key=True, index=True, autoincrement=True)
    premio_id     = Column(Integer, ForeignKey("premios.id"), nullable=False)
    email_cliente = Column(String(150), nullable=False, index=True)  # Email del beneficiario
    entregado     = Column(Boolean, default=False)   # Si ya fue asignado al cliente
    created_at    = Column(DateTime(timezone=True), server_default=func.now())

    premio = relationship("Premio", back_populates="condicionados")


# ─────────────────────────────────────────────────────────
# MODELO: Cliente
# Portado y enriquecido desde el proyecto Django.
# Se conservan TODOS los campos del modelo antiguo.
# La lógica de gestionar_acciones() se mueve a:
#   → app/services/cliente_service.py
# ─────────────────────────────────────────────────────────
class Cliente(Base):
    __tablename__ = "clientes"

    id         = Column(Integer, primary_key=True, index=True, autoincrement=True)
    agencia_id = Column(Integer, ForeignKey("agencias.id"), nullable=True)

    # Campos portados del modelo Django antiguo
    nombres    = Column(String(150), nullable=True)
    apellidos  = Column(String(150), nullable=True)
    email      = Column(String(150), unique=True, index=True, nullable=False)
    token      = Column(String(50),  unique=True, index=True, nullable=True)   # max=50 del antiguo
    celular    = Column(String(50),  nullable=True)
    direccion  = Column(Text, nullable=True)
    fecha_nacimiento = Column(Date, nullable=True)
    cargo            = Column(String(150), nullable=True)
    fecha_acceso     = Column(Date, nullable=True)     # Cuándo accedió al sistema
    fecha_completo   = Column(Date, nullable=True)     # Cuándo completó su registro
    genero           = Column(SAEnum(GeneroCliente), default=GeneroCliente.sin_dato)

    # Pregunta y respuesta de seguridad (portados desde Django)
    pregunta_seguridad_id = Column(Integer, ForeignKey("preguntas_seguridad.id"), nullable=True)
    respuesta_seguridad   = Column(Text, nullable=True)

    # Premio asignado al cliente (FK directa, portado del modelo Django)
    # Representa el premio que ganó o que fue condicionado para él
    premio_id = Column(Integer, ForeignKey("premios.id"), nullable=True)

    # Estatus en el flujo (portado desde tabla EstatusCliente del antiguo)
    estatus     = Column(SAEnum(EstatusCliente), default=EstatusCliente.anadido)
    token_usado = Column(Boolean, default=False)

    # Portado: en el antiguo era IntegerField; aquí es FK para integridad referencial
    referido_por_id = Column(Integer, ForeignKey("clientes.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relaciones
    agencia            = relationship("Agencia", back_populates="clientes")
    pregunta_seguridad = relationship("PreguntaSeguridad", back_populates="clientes")
    premio             = relationship("Premio", back_populates="clientes")
    participaciones    = relationship("Participacion", back_populates="cliente")
    correos_log        = relationship("CorreoLog", back_populates="cliente")
    referidos          = relationship("Cliente", foreign_keys=[referido_por_id])


# ─────────────────────────────────────────────────────────
# MODELO: Participacion
# Registro de cada giro realizado por un cliente
# ─────────────────────────────────────────────────────────
class Participacion(Base):
    __tablename__ = "participaciones"

    id                  = Column(Integer, primary_key=True, index=True, autoincrement=True)
    cliente_id          = Column(Integer, ForeignKey("clientes.id"), nullable=False)
    ruleta_id           = Column(Integer, ForeignKey("ruletas.id"),  nullable=False)
    premio_id           = Column(Integer, ForeignKey("premios.id"),  nullable=True)
    fecha_participacion = Column(DateTime(timezone=True), server_default=func.now())
    premio_entregado    = Column(Boolean, default=False)
    token_usado         = Column(String(50), nullable=True)   # max=50 alineado con token de Cliente

    cliente = relationship("Cliente", back_populates="participaciones")
    ruleta  = relationship("Ruleta",  back_populates="participaciones")
    premio  = relationship("Premio",  back_populates="participaciones")


# ─────────────────────────────────────────────────────────
# MODELO: CorreoLog
# Historial de todos los correos enviados
# ─────────────────────────────────────────────────────────
class CorreoLog(Base):
    __tablename__ = "correos_log"

    id          = Column(Integer, primary_key=True, index=True, autoincrement=True)
    cliente_id  = Column(Integer, ForeignKey("clientes.id"), nullable=False)
    tipo        = Column(SAEnum(TipoCorreo),   nullable=False)
    estado      = Column(SAEnum(EstadoCorreo), default=EstadoCorreo.pendiente)
    asunto      = Column(String(255), nullable=True)
    fecha_envio = Column(DateTime(timezone=True), server_default=func.now())
    lote_id     = Column(String(50), nullable=True)   # ID del lote de envío masivo
    error_msg   = Column(Text, nullable=True)

    cliente = relationship("Cliente", back_populates="correos_log")
