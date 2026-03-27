"""
=====================================================
SCHEMAS PYDANTIC - GIRO DE RULETA
=====================================================
Descripción: Validación de entrada y salida para
             el endpoint de giro de la ruleta.
=====================================================
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# ── Entrada del giro ─────────────────────────────
class GiroRequest(BaseModel):
    token: str = Field(..., min_length=10, description="Token único del cliente")
    ruleta_id: int = Field(..., description="ID de la ruleta a girar")


# ── Respuesta del giro ───────────────────────────
class GiroResponse(BaseModel):
    participacion_id: int
    cliente_id:       int
    cliente_email:    str
    ruleta_id:        int
    ruleta_nombre:    str
    premio_id:        Optional[int]   = None
    premio_nombre:    Optional[str]   = None
    premio_imagen:    Optional[str]   = None
    es_condicionado:  bool            = False
    fecha:            datetime
    mensaje:          str

    class Config:
        from_attributes = True


# ── Schema para estadísticas ──────────────────────
class EstadisticaRuleta(BaseModel):
    ruleta_id:           int
    ruleta_nombre:       str
    total_clientes:      int
    total_participaciones: int
    porcentaje_participacion: float
    premios_entregados:  int
    premios_disponibles: int


class EstadisticaAgencia(BaseModel):
    agencia_id:    int
    agencia_nombre: str
    total_clientes: int
    participaron:   int
    porcentaje:     float


class ReporteResponse(BaseModel):
    ruleta:    EstadisticaRuleta
    agencias:  list[EstadisticaAgencia]
    ganadores: list[dict]
