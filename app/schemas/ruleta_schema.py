"""
=====================================================
SCHEMAS PYDANTIC - RULETAS
=====================================================
Descripción: Define los esquemas de validación y serialización
             para el modelo Ruleta usando Pydantic v2.
             Separa los datos de entrada (request) y salida (response).
=====================================================
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# ─────────────────────────────────────────────
# SCHEMA BASE: Campos comunes de una Ruleta
# ─────────────────────────────────────────────
class RuletaBase(BaseModel):
    nombre: str = Field(
        ..., min_length=3, max_length=150, description="Nombre del evento de ruleta"
    )
    descripcion: Optional[str] = Field(
        None, description="Descripción opcional del evento"
    )
    fecha_inicio: datetime = Field(..., description="Fecha y hora de inicio del evento")
    fecha_cierre: Optional[datetime] = Field(
        None, description="Fecha y hora de cierre del evento"
    )
    activa: bool = Field(
        True, description="Si la ruleta está habilitada para participar"
    )
    max_giros: int = Field(
        1, ge=1, description="Máximo de giros permitidos por cliente"
    )
    tema: Optional[str] = Field(None, description="Tema visual de la ruleta")
    tema_imagen: Optional[str] = Field(None, description="URL de imagen del tema")
    tema_color1: Optional[str] = Field(None, description="Color primario del tema")
    tema_color2: Optional[str] = Field(None, description="Color secundario del tema")
    tema_color3: Optional[str] = Field(None, description="Color terciario del tema")


# ─────────────────────────────────────────────
# SCHEMA CREACIÓN: Datos para registrar una ruleta
# ─────────────────────────────────────────────
class RuletaCreate(RuletaBase):
    """
    Esquema usado al crear una nueva ruleta.
    Hereda todos los campos base sin modificaciones.
    """

    pass


# ─────────────────────────────────────────────
# SCHEMA ACTUALIZACIÓN: Todos los campos opcionales
# Permite actualizaciones parciales (PATCH)
# ─────────────────────────────────────────────
class RuletaUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=3, max_length=150)
    descripcion: Optional[str] = None
    fecha_inicio: Optional[datetime] = None
    fecha_cierre: Optional[datetime] = None
    activa: Optional[bool] = None
    max_giros: Optional[int] = Field(None, ge=1)
    tema: Optional[str] = Field(None)
    tema_imagen: Optional[str] = Field(None)
    tema_color1: Optional[str] = Field(None)
    tema_color2: Optional[str] = Field(None)
    tema_color3: Optional[str] = Field(None)


# ─────────────────────────────────────────────
# SCHEMA RESPUESTA: Lo que se devuelve al cliente
# Incluye campos generados automáticamente por la BD
# ─────────────────────────────────────────────
class RuletaResponse(RuletaBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True  # Permite convertir modelos ORM a este schema


# ─────────────────────────────────────────────
# SCHEMA PAGINACIÓN: Respuesta con lista paginada
# ─────────────────────────────────────────────
class RuletaListResponse(BaseModel):
    total: int = Field(..., description="Total de registros en la base de datos")
    pagina: int = Field(..., description="Página actual")
    por_pagina: int = Field(..., description="Registros por página (máx. 20)")
    paginas_totales: int = Field(..., description="Total de páginas disponibles")
    datos: list[RuletaResponse] = Field(
        ..., description="Lista de ruletas en la página actual"
    )
