"""
=====================================================
SCHEMAS PYDANTIC - PREMIOS
=====================================================
Descripción: Validación para premios con control
             de inventario y premios condicionados.
=====================================================
"""
from pydantic import BaseModel, Field, model_validator
from typing import Optional
from datetime import datetime


class PremioBase(BaseModel):
    ruleta_id:          int            = Field(..., description="ID de la ruleta a la que pertenece")
    nombre:             str            = Field(..., min_length=2, max_length=150)
    cantidad_total:     int            = Field(..., ge=0, description="Total de unidades en stock")
    cantidad_disponible: int           = Field(..., ge=0, description="Unidades aún por asignar")
    cantidad_entregada: int            = Field(0,  ge=0, description="Unidades ya entregadas")
    porcentaje_prob:    float          = Field(0.0, ge=0.0, le=100.0, description="Probabilidad de ganar (%)")
    imagen_url:         Optional[str]  = Field(None, max_length=255)
    es_condicionado:    bool           = Field(False, description="Si es un premio reservado para clientes específicos")

    @model_validator(mode="after")
    def validar_cantidades(self):
        """La cantidad disponible no puede superar la total."""
        if self.cantidad_disponible > self.cantidad_total:
            raise ValueError("cantidad_disponible no puede ser mayor que cantidad_total")
        if self.cantidad_entregada > self.cantidad_total:
            raise ValueError("cantidad_entregada no puede ser mayor que cantidad_total")
        return self


class PremioCreate(PremioBase):
    pass


class PremioUpdate(BaseModel):
    nombre:              Optional[str]   = Field(None, min_length=2, max_length=150)
    cantidad_total:      Optional[int]   = Field(None, ge=0)
    cantidad_disponible: Optional[int]   = Field(None, ge=0)
    cantidad_entregada:  Optional[int]   = Field(None, ge=0)
    porcentaje_prob:     Optional[float] = Field(None, ge=0.0, le=100.0)
    imagen_url:          Optional[str]   = Field(None, max_length=255)
    es_condicionado:     Optional[bool]  = None


class PremioResponse(PremioBase):
    id:         int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PremioListResponse(BaseModel):
    total:           int
    pagina:          int
    por_pagina:      int
    paginas_totales: int
    datos:           list[PremioResponse]


# ─────────────────────────────────────────────
# SCHEMA: Premio Condicionado
# ─────────────────────────────────────────────
class PremioCondicionadoBase(BaseModel):
    premio_id:     int = Field(..., description="ID del premio a reservar")
    email_cliente: str = Field(..., description="Email del cliente beneficiario")


class PremioCondicionadoCreate(PremioCondicionadoBase):
    pass


class PremioCondicionadoResponse(PremioCondicionadoBase):
    id:         int
    entregado:  bool
    created_at: datetime

    class Config:
        from_attributes = True


class PremioCondicionadoListResponse(BaseModel):
    total:           int
    pagina:          int
    por_pagina:      int
    paginas_totales: int
    datos:           list[PremioCondicionadoResponse]
