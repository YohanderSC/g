"""
=====================================================
SCHEMAS PYDANTIC - AGENCIAS
=====================================================
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class AgenciaBase(BaseModel):
    nombre:      str            = Field(..., min_length=2, max_length=150)
    descripcion: Optional[str] = None
    ciudad:      Optional[str] = Field(None, max_length=100)
    direccion:   Optional[str] = Field(None, max_length=255)
    activa:      bool           = True


class AgenciaCreate(AgenciaBase):
    pass


class AgenciaUpdate(BaseModel):
    nombre:      Optional[str]  = Field(None, min_length=2, max_length=150)
    descripcion: Optional[str]  = None
    ciudad:      Optional[str]  = Field(None, max_length=100)
    direccion:   Optional[str]  = Field(None, max_length=255)
    activa:      Optional[bool] = None


class AgenciaResponse(AgenciaBase):
    id:         int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AgenciaListResponse(BaseModel):
    total:          int
    pagina:         int
    por_pagina:     int
    paginas_totales: int
    datos:          list[AgenciaResponse]
