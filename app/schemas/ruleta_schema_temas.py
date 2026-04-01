"""
SCHEMAS PYDANTIC - RULETAS (actualizado con temas)
Agregar a app/schemas/ruleta_schema.py
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class RuletaBase(BaseModel):
    nombre:       str           = Field(..., min_length=3, max_length=150)
    descripcion:  Optional[str] = None
    fecha_inicio: datetime      = Field(...)
    fecha_cierre: Optional[datetime] = None
    activa:       bool          = True
    max_giros:    int           = Field(1, ge=1)
    # ── Campos de tema ────────────────────────────
    tema:         Optional[str] = Field('default', description="Nombre del tema predefinido")
    tema_imagen:  Optional[str] = Field(None, max_length=500, description="URL de imagen de referencia del evento")
    tema_color1:  Optional[str] = Field(None, max_length=7, description="Color primario #RRGGBB")
    tema_color2:  Optional[str] = Field(None, max_length=7, description="Color secundario #RRGGBB")
    tema_color3:  Optional[str] = Field(None, max_length=7, description="Color acento #RRGGBB")


class RuletaCreate(RuletaBase):
    pass


class RuletaUpdate(BaseModel):
    nombre:       Optional[str]      = Field(None, min_length=3, max_length=150)
    descripcion:  Optional[str]      = None
    fecha_inicio: Optional[datetime] = None
    fecha_cierre: Optional[datetime] = None
    activa:       Optional[bool]     = None
    max_giros:    Optional[int]      = Field(None, ge=1)
    tema:         Optional[str]      = None
    tema_imagen:  Optional[str]      = Field(None, max_length=500)
    tema_color1:  Optional[str]      = Field(None, max_length=7)
    tema_color2:  Optional[str]      = Field(None, max_length=7)
    tema_color3:  Optional[str]      = Field(None, max_length=7)


class RuletaResponse(RuletaBase):
    id:         int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class RuletaListResponse(BaseModel):
    total:           int
    pagina:          int
    por_pagina:      int
    paginas_totales: int
    datos:           list[RuletaResponse]
