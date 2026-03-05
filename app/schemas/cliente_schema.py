"""
=====================================================
SCHEMAS PYDANTIC - CLIENTES
=====================================================
Descripción: Validación para clientes incluyendo
             importación masiva desde XLSX/CSV.
=====================================================
"""
from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import datetime, date
from app.models.models import GeneroCliente, EstatusCliente


# ─────────────────────────────────────────────
# SCHEMA BASE
# ─────────────────────────────────────────────
class ClienteBase(BaseModel):
    email:      EmailStr        = Field(..., description="Email único del cliente")
    nombres:    Optional[str]  = Field(None, max_length=150)
    apellidos:  Optional[str]  = Field(None, max_length=150)
    celular:    Optional[str]  = Field(None, max_length=50)
    direccion:  Optional[str]  = None
    cargo:      Optional[str]  = Field(None, max_length=150)
    genero:     GeneroCliente  = GeneroCliente.sin_dato
    fecha_nacimiento:          Optional[date] = None
    agencia_id:                Optional[int]  = None
    pregunta_seguridad_id:     Optional[int]  = None
    respuesta_seguridad:       Optional[str]  = None


class ClienteCreate(ClienteBase):
    pass


class ClienteUpdate(BaseModel):
    nombres:               Optional[str]          = Field(None, max_length=150)
    apellidos:             Optional[str]          = Field(None, max_length=150)
    celular:               Optional[str]          = Field(None, max_length=50)
    direccion:             Optional[str]          = None
    cargo:                 Optional[str]          = Field(None, max_length=150)
    genero:                Optional[GeneroCliente] = None
    fecha_nacimiento:      Optional[date]         = None
    agencia_id:            Optional[int]          = None
    pregunta_seguridad_id: Optional[int]          = None
    respuesta_seguridad:   Optional[str]          = None
    estatus:               Optional[EstatusCliente] = None
    premio_id:             Optional[int]          = None


class ClienteResponse(ClienteBase):
    id:              int
    token:           Optional[str]          = None
    token_usado:     bool
    estatus:         EstatusCliente
    premio_id:       Optional[int]          = None
    referido_por_id: Optional[int]          = None
    fecha_acceso:    Optional[date]         = None
    fecha_completo:  Optional[date]         = None
    created_at:      datetime
    updated_at:      Optional[datetime]     = None

    class Config:
        from_attributes = True


class ClienteListResponse(BaseModel):
    total:           int
    pagina:          int
    por_pagina:      int
    paginas_totales: int
    datos:           list[ClienteResponse]


# ─────────────────────────────────────────────
# SCHEMA: Resultado de importación masiva
# ─────────────────────────────────────────────
class ImportacionFila(BaseModel):
    """Representa una fila del archivo XLSX/CSV durante la importación."""
    fila:    int
    email:   str
    nombres: Optional[str] = None
    estado:  str   # "importado", "duplicado", "error"
    detalle: Optional[str] = None


class ImportacionResponse(BaseModel):
    """Respuesta completa luego de procesar el archivo de importación."""
    archivo:     str
    total_filas: int
    importados:  int
    duplicados:  int
    errores:     int
    detalle:     list[ImportacionFila]
