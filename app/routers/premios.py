"""
=====================================================
ROUTER - PREMIOS (CRUD + INVENTARIO + CONDICIONADOS)
=====================================================
Endpoints Premios:
  POST   /premios/                    → Crear premio
  GET    /premios/                    → Listar (paginado, filtro por ruleta)
  GET    /premios/{id}                → Consultar por ID
  PATCH  /premios/{id}                → Editar / ajustar inventario
  DELETE /premios/{id}                → Eliminar
  PATCH  /premios/{id}/entregar       → Registrar entrega de una unidad

Endpoints Premios Condicionados:
  POST   /premios/condicionados/               → Asignar premio a cliente específico
  GET    /premios/condicionados/               → Listar condicionados
  DELETE /premios/condicionados/{id}           → Eliminar condicionado
=====================================================
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
import math

from app.database.database import get_db
from app.models.models import Premio, PremioCondicionado, Ruleta
from app.schemas.premio_schema import (
    PremioCreate, PremioUpdate, PremioResponse, PremioListResponse,
    PremioCondicionadoCreate, PremioCondicionadoResponse, PremioCondicionadoListResponse
)

router = APIRouter(prefix="/premios", tags=["Premios"])
POR_PAGINA = 20


# ──────────────────────────────────────────────────────
# PREMIOS - CRUD
# ──────────────────────────────────────────────────────

@router.post("/", response_model=PremioResponse, status_code=status.HTTP_201_CREATED,
             summary="Crear premio")
def crear_premio(datos: PremioCreate, db: Session = Depends(get_db)):
    # Verificar que la ruleta existe
    ruleta = db.query(Ruleta).filter(Ruleta.id == datos.ruleta_id).first()
    if not ruleta:
        raise HTTPException(status_code=404, detail=f"Ruleta {datos.ruleta_id} no encontrada.")

    premio = Premio(**datos.model_dump())
    db.add(premio)
    db.commit()
    db.refresh(premio)
    return premio


@router.get("/", response_model=PremioListResponse, summary="Listar premios paginados")
def listar_premios(
    pagina:     int           = Query(1, ge=1),
    ruleta_id:  int | None    = Query(None, description="Filtrar por ruleta"),
    disponibles: bool         = Query(False, description="Solo con cantidad_disponible > 0"),
    db: Session = Depends(get_db)
):
    query = db.query(Premio)

    if ruleta_id:
        query = query.filter(Premio.ruleta_id == ruleta_id)
    if disponibles:
        query = query.filter(Premio.cantidad_disponible > 0)

    total           = query.count()
    paginas_totales = math.ceil(total / POR_PAGINA) if total > 0 else 1
    datos           = query.order_by(Premio.nombre).offset((pagina - 1) * POR_PAGINA).limit(POR_PAGINA).all()

    return {"total": total, "pagina": pagina, "por_pagina": POR_PAGINA,
            "paginas_totales": paginas_totales, "datos": datos}


@router.get("/{premio_id}", response_model=PremioResponse, summary="Consultar premio por ID")
def obtener_premio(premio_id: int, db: Session = Depends(get_db)):
    premio = db.query(Premio).filter(Premio.id == premio_id).first()
    if not premio:
        raise HTTPException(status_code=404, detail=f"Premio {premio_id} no encontrado.")
    return premio


@router.patch("/{premio_id}", response_model=PremioResponse, summary="Editar premio / ajustar inventario")
def editar_premio(premio_id: int, datos: PremioUpdate, db: Session = Depends(get_db)):
    premio = db.query(Premio).filter(Premio.id == premio_id).first()
    if not premio:
        raise HTTPException(status_code=404, detail=f"Premio {premio_id} no encontrado.")

    cambios = datos.model_dump(exclude_unset=True)

    # Validar inventario con los nuevos valores
    nuevo_total      = cambios.get("cantidad_total",      premio.cantidad_total)
    nuevo_disponible = cambios.get("cantidad_disponible", premio.cantidad_disponible)
    nuevo_entregado  = cambios.get("cantidad_entregada",  premio.cantidad_entregada)

    if nuevo_disponible > nuevo_total:
        raise HTTPException(status_code=400, detail="cantidad_disponible no puede superar cantidad_total.")
    if nuevo_entregado > nuevo_total:
        raise HTTPException(status_code=400, detail="cantidad_entregada no puede superar cantidad_total.")

    for campo, valor in cambios.items():
        setattr(premio, campo, valor)

    db.commit()
    db.refresh(premio)
    return premio


@router.patch("/{premio_id}/entregar", response_model=PremioResponse,
              summary="Registrar entrega de una unidad del premio")
def entregar_premio(premio_id: int, db: Session = Depends(get_db)):
    """
    Descuenta 1 de cantidad_disponible y suma 1 a cantidad_entregada.
    Se llama cuando un cliente recibe físicamente su premio.
    """
    premio = db.query(Premio).filter(Premio.id == premio_id).first()
    if not premio:
        raise HTTPException(status_code=404, detail=f"Premio {premio_id} no encontrado.")
    if premio.cantidad_disponible <= 0:
        raise HTTPException(status_code=400,
                            detail=f"El premio '{premio.nombre}' no tiene unidades disponibles.")

    premio.cantidad_disponible -= 1
    premio.cantidad_entregada  += 1

    db.commit()
    db.refresh(premio)
    return premio


@router.delete("/{premio_id}", status_code=status.HTTP_200_OK, summary="Eliminar premio")
def eliminar_premio(premio_id: int, db: Session = Depends(get_db)):
    premio = db.query(Premio).filter(Premio.id == premio_id).first()
    if not premio:
        raise HTTPException(status_code=404, detail=f"Premio {premio_id} no encontrado.")
    db.delete(premio)
    db.commit()
    return {"mensaje": f"Premio {premio_id} eliminado.", "id_eliminado": premio_id}


# ──────────────────────────────────────────────────────
# PREMIOS CONDICIONADOS
# ──────────────────────────────────────────────────────

@router.post("/condicionados/", response_model=PremioCondicionadoResponse,
             status_code=status.HTTP_201_CREATED,
             summary="Asignar premio condicionado a cliente específico")
def crear_condicionado(datos: PremioCondicionadoCreate, db: Session = Depends(get_db)):
    """
    Reserva un premio para un cliente específico por su email.
    Reemplaza las listas hardcodeadas del proyecto Django anterior.
    """
    # Verificar que el premio existe y es condicionado
    premio = db.query(Premio).filter(Premio.id == datos.premio_id).first()
    if not premio:
        raise HTTPException(status_code=404, detail=f"Premio {datos.premio_id} no encontrado.")
    if not premio.es_condicionado:
        raise HTTPException(status_code=400,
                            detail="El premio debe tener es_condicionado=True para asignarse de esta forma.")

    # Verificar que no existe ya una asignación pendiente para ese email/premio
    existente = db.query(PremioCondicionado).filter(
        PremioCondicionado.premio_id     == datos.premio_id,
        PremioCondicionado.email_cliente == datos.email_cliente,
        PremioCondicionado.entregado     == False
    ).first()
    if existente:
        raise HTTPException(status_code=400,
                            detail=f"Ya existe una asignación pendiente del premio {datos.premio_id} para {datos.email_cliente}.")

    condicionado = PremioCondicionado(**datos.model_dump())
    db.add(condicionado)
    db.commit()
    db.refresh(condicionado)
    return condicionado


@router.get("/condicionados/", response_model=PremioCondicionadoListResponse,
            summary="Listar premios condicionados")
def listar_condicionados(
    pagina:    int       = Query(1, ge=1),
    premio_id: int | None = Query(None, description="Filtrar por premio"),
    entregado: bool | None = Query(None, description="Filtrar por estado de entrega"),
    db: Session = Depends(get_db)
):
    query = db.query(PremioCondicionado)
    if premio_id:
        query = query.filter(PremioCondicionado.premio_id == premio_id)
    if entregado is not None:
        query = query.filter(PremioCondicionado.entregado == entregado)

    total           = query.count()
    paginas_totales = math.ceil(total / POR_PAGINA) if total > 0 else 1
    datos           = query.order_by(PremioCondicionado.id).offset((pagina - 1) * POR_PAGINA).limit(POR_PAGINA).all()

    return {"total": total, "pagina": pagina, "por_pagina": POR_PAGINA,
            "paginas_totales": paginas_totales, "datos": datos}


@router.delete("/condicionados/{condicionado_id}", status_code=status.HTTP_200_OK,
               summary="Eliminar asignación condicionada")
def eliminar_condicionado(condicionado_id: int, db: Session = Depends(get_db)):
    cond = db.query(PremioCondicionado).filter(PremioCondicionado.id == condicionado_id).first()
    if not cond:
        raise HTTPException(status_code=404, detail=f"Asignación {condicionado_id} no encontrada.")
    db.delete(cond)
    db.commit()
    return {"mensaje": f"Asignación {condicionado_id} eliminada.", "id_eliminado": condicionado_id}
