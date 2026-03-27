"""
=====================================================
MODELO ORM - ENCUESTAS
=====================================================
PreguntaEncuesta: preguntas configuradas por el admin
RespuestaEncuesta: respuestas dadas por los clientes

Tipos de pregunta:
  texto_libre    → campo de texto abierto
  opcion_multiple → selección de una opción
  si_no          → botones Sí / No
  escala         → puntuación del 1 al 5
=====================================================
"""
import enum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.database import Base


class TipoPregunta(str, enum.Enum):
    texto_libre     = "texto_libre"
    opcion_multiple = "opcion_multiple"
    si_no           = "si_no"
    escala          = "escala"


class PreguntaEncuesta(Base):
    __tablename__ = "preguntas_encuesta"

    id         = Column(Integer, primary_key=True, index=True, autoincrement=True)
    texto      = Column(Text, nullable=False)
    tipo       = Column(SAEnum(TipoPregunta), default=TipoPregunta.texto_libre)
    opciones   = Column(Text, nullable=True)   # JSON string: ["Opción A","Opción B"]
    obligatoria = Column(Boolean, default=False)
    activa     = Column(Boolean, default=True)
    orden      = Column(Integer, default=0)    # Para ordenar las preguntas
    # Si ruleta_id es NULL aplica a todas las ruletas
    ruleta_id  = Column(Integer, ForeignKey("ruletas.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    ruleta     = relationship("Ruleta", foreign_keys=[ruleta_id])
    respuestas = relationship("RespuestaEncuesta", back_populates="pregunta")


class RespuestaEncuesta(Base):
    __tablename__ = "respuestas_encuesta"

    id           = Column(Integer, primary_key=True, index=True, autoincrement=True)
    pregunta_id  = Column(Integer, ForeignKey("preguntas_encuesta.id"), nullable=False)
    cliente_id   = Column(Integer, ForeignKey("clientes.id"), nullable=False)
    ruleta_id    = Column(Integer, ForeignKey("ruletas.id"), nullable=True)
    respuesta    = Column(Text, nullable=False)
    fecha        = Column(DateTime(timezone=True), server_default=func.now())

    pregunta = relationship("PreguntaEncuesta", back_populates="respuestas")
    cliente  = relationship("Cliente",  foreign_keys=[cliente_id])
    ruleta   = relationship("Ruleta",   foreign_keys=[ruleta_id])
