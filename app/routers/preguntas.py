"""
=====================================================
ROUTER - PREGUNTAS DE SEGURIDAD (CRUD COMPLETO)
=====================================================
Endpoints:
  POST   /preguntas/       → Crear pregunta
  GET    /preguntas/       → Listar (paginado)
  GET    /preguntas/{id}   → Consultar por ID
  PATCH  /preguntas/{id}   → Editar
  DELETE /preguntas/{id}   → Eliminar
=====================================================
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
import math

from app.database.database import get_db
from app.models.models import PreguntaSeguridad
from app.schemas.pregunta_schema import (
    PreguntaCreate, PreguntaUpdate, PreguntaResponse, PreguntaListResponse
)

router = APIRouter(prefix="/preguntas", tags=["Preguntas de Seguridad"])
POR_PAGINA = 20


@router.post("/", response_model=PreguntaResponse, status_code=status.HTTP_201_CREATED,
             summary="Crear pregunta de seguridad")
def crear_pregunta(datos: PreguntaCreate, db: Session = Depends(get_db)):
    pregunta = PreguntaSeguridad(**datos.model_dump())
    db.add(pregunta)
    db.commit()
    db.refresh(pregunta)
    return pregunta


@router.get("/", response_model=PreguntaListResponse, summary="Listar preguntas paginadas")
def listar_preguntas(
    pagina:       int  = Query(1, ge=1),
    solo_activas: bool = Query(True, description="Mostrar solo preguntas activas"),
    db: Session = Depends(get_db)
):
    query = db.query(PreguntaSeguridad)
    if solo_activas:
        query = query.filter(PreguntaSeguridad.activa == True)

    total           = query.count()
    paginas_totales = math.ceil(total / POR_PAGINA) if total > 0 else 1
    datos           = query.order_by(PreguntaSeguridad.id).offset((pagina - 1) * POR_PAGINA).limit(POR_PAGINA).all()

    return {"total": total, "pagina": pagina, "por_pagina": POR_PAGINA,
            "paginas_totales": paginas_totales, "datos": datos}


@router.get("/{pregunta_id}", response_model=PreguntaResponse, summary="Consultar pregunta por ID")
def obtener_pregunta(pregunta_id: int, db: Session = Depends(get_db)):
    pregunta = db.query(PreguntaSeguridad).filter(PreguntaSeguridad.id == pregunta_id).first()
    if not pregunta:
        raise HTTPException(status_code=404, detail=f"Pregunta {pregunta_id} no encontrada.")
    return pregunta


@router.patch("/{pregunta_id}", response_model=PreguntaResponse, summary="Editar pregunta")
def editar_pregunta(pregunta_id: int, datos: PreguntaUpdate, db: Session = Depends(get_db)):
    pregunta = db.query(PreguntaSeguridad).filter(PreguntaSeguridad.id == pregunta_id).first()
    if not pregunta:
        raise HTTPException(status_code=404, detail=f"Pregunta {pregunta_id} no encontrada.")

    for campo, valor in datos.model_dump(exclude_unset=True).items():
        setattr(pregunta, campo, valor)

    db.commit()
    db.refresh(pregunta)
    return pregunta


@router.delete("/{pregunta_id}", status_code=status.HTTP_200_OK, summary="Eliminar pregunta")
def eliminar_pregunta(pregunta_id: int, db: Session = Depends(get_db)):
    pregunta = db.query(PreguntaSeguridad).filter(PreguntaSeguridad.id == pregunta_id).first()
    if not pregunta:
        raise HTTPException(status_code=404, detail=f"Pregunta {pregunta_id} no encontrada.")
    db.delete(pregunta)
    db.commit()
    return {"mensaje": f"Pregunta {pregunta_id} eliminada.", "id_eliminado": pregunta_id}
