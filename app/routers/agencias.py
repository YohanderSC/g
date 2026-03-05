"""
=====================================================
ROUTER - AGENCIAS (CRUD COMPLETO)
=====================================================
Endpoints:
  POST   /agencias/        → Crear agencia
  GET    /agencias/        → Listar (paginado 20/página)
  GET    /agencias/{id}    → Consultar por ID
  PATCH  /agencias/{id}    → Editar
  DELETE /agencias/{id}    → Eliminar
=====================================================
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
import math

from app.database.database import get_db
from app.models.models import Agencia
from app.schemas.agencia_schema import (
    AgenciaCreate, AgenciaUpdate, AgenciaResponse, AgenciaListResponse
)

router = APIRouter(prefix="/agencias", tags=["Agencias"])
POR_PAGINA = 20


@router.post("/", response_model=AgenciaResponse, status_code=status.HTTP_201_CREATED,
             summary="Crear agencia")
def crear_agencia(datos: AgenciaCreate, db: Session = Depends(get_db)):
    agencia = Agencia(**datos.model_dump())
    db.add(agencia)
    db.commit()
    db.refresh(agencia)
    return agencia


@router.get("/", response_model=AgenciaListResponse, summary="Listar agencias paginadas")
def listar_agencias(
    pagina:       int  = Query(1, ge=1),
    solo_activas: bool = Query(False, description="Filtrar solo agencias activas"),
    db: Session = Depends(get_db)
):
    query = db.query(Agencia)
    if solo_activas:
        query = query.filter(Agencia.activa == True)

    total          = query.count()
    paginas_totales = math.ceil(total / POR_PAGINA) if total > 0 else 1
    datos          = query.order_by(Agencia.nombre).offset((pagina - 1) * POR_PAGINA).limit(POR_PAGINA).all()

    return {"total": total, "pagina": pagina, "por_pagina": POR_PAGINA,
            "paginas_totales": paginas_totales, "datos": datos}


@router.get("/{agencia_id}", response_model=AgenciaResponse, summary="Consultar agencia por ID")
def obtener_agencia(agencia_id: int, db: Session = Depends(get_db)):
    agencia = db.query(Agencia).filter(Agencia.id == agencia_id).first()
    if not agencia:
        raise HTTPException(status_code=404, detail=f"Agencia {agencia_id} no encontrada.")
    return agencia


@router.patch("/{agencia_id}", response_model=AgenciaResponse, summary="Editar agencia")
def editar_agencia(agencia_id: int, datos: AgenciaUpdate, db: Session = Depends(get_db)):
    agencia = db.query(Agencia).filter(Agencia.id == agencia_id).first()
    if not agencia:
        raise HTTPException(status_code=404, detail=f"Agencia {agencia_id} no encontrada.")

    for campo, valor in datos.model_dump(exclude_unset=True).items():
        setattr(agencia, campo, valor)

    db.commit()
    db.refresh(agencia)
    return agencia


@router.delete("/{agencia_id}", status_code=status.HTTP_200_OK, summary="Eliminar agencia")
def eliminar_agencia(agencia_id: int, db: Session = Depends(get_db)):
    agencia = db.query(Agencia).filter(Agencia.id == agencia_id).first()
    if not agencia:
        raise HTTPException(status_code=404, detail=f"Agencia {agencia_id} no encontrada.")
    db.delete(agencia)
    db.commit()
    return {"mensaje": f"Agencia {agencia_id} eliminada.", "id_eliminado": agencia_id}
