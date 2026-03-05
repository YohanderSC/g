"""
=====================================================
SCHEMAS PYDANTIC - PREGUNTAS DE SEGURIDAD
=====================================================
"""
from pydantic import BaseModel, Field
from typing import Optional


class PreguntaBase(BaseModel):
    pregunta: str  = Field(..., min_length=5, description="Texto de la pregunta de seguridad")
    activa:   bool = True


class PreguntaCreate(PreguntaBase):
    pass


class PreguntaUpdate(BaseModel):
    pregunta: Optional[str]  = Field(None, min_length=5)
    activa:   Optional[bool] = None


class PreguntaResponse(PreguntaBase):
    id: int

    class Config:
        from_attributes = True


class PreguntaListResponse(BaseModel):
    total:          int
    pagina:         int
    por_pagina:     int
    paginas_totales: int
    datos:          list[PreguntaResponse]
