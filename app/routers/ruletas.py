"""
=====================================================
ROUTER - RULETAS (CRUD COMPLETO)
=====================================================
Descripción: Endpoints REST para gestión de ruletas.
             Incluye: registrar, listar con paginación,
             consultar por ID, editar y eliminar.

Endpoints:
  POST   /ruletas/           → Crear nueva ruleta
  GET    /ruletas/           → Listar ruletas (paginado, 20 x página)
  GET    /ruletas/{id}       → Consultar ruleta por ID
  PATCH  /ruletas/{id}       → Editar ruleta (campos opcionales)
  DELETE /ruletas/{id}       → Eliminar ruleta
=====================================================
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import math

from app.database.database import get_db
from app.models.models import Ruleta
from app.schemas.ruleta_schema import (
    RuletaCreate,
    RuletaUpdate,
    RuletaResponse,
    RuletaListResponse
)

# Instancia del router con prefijo y etiqueta para la documentación Swagger
router = APIRouter(
    prefix="/ruletas",
    tags=["Ruletas"]
)

# Número fijo de registros por página (requerimiento del negocio)
REGISTROS_POR_PAGINA = 20


# ─────────────────────────────────────────────
# ENDPOINT 1: CREAR RULETA
# POST /ruletas/
# ─────────────────────────────────────────────
@router.post(
    "/",
    response_model=RuletaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar nueva ruleta",
    description="Crea un nuevo evento de ruleta en el sistema."
)
def crear_ruleta(
    datos: RuletaCreate,
    db: Session = Depends(get_db)
):
    """
    Registra una nueva ruleta con sus datos de configuración.
    Valida que la fecha de cierre sea posterior a la de inicio.
    """
    # Validar que fecha_cierre sea posterior a fecha_inicio
    if datos.fecha_cierre and datos.fecha_cierre <= datos.fecha_inicio:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La fecha de cierre debe ser posterior a la fecha de inicio."
        )

    # Crear instancia del modelo con los datos recibidos
    nueva_ruleta = Ruleta(**datos.model_dump())

    try:
        db.add(nueva_ruleta)       # Agregar a la sesión de BD
        db.commit()                # Confirmar la transacción
        db.refresh(nueva_ruleta)   # Recargar para obtener ID y timestamps
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error al guardar la ruleta. Verifique los datos enviados."
        )

    return nueva_ruleta


# ─────────────────────────────────────────────
# ENDPOINT 2: LISTAR RULETAS CON PAGINACIÓN
# GET /ruletas/?pagina=1
# ─────────────────────────────────────────────
@router.get(
    "/",
    response_model=RuletaListResponse,
    summary="Listar ruletas paginadas",
    description="Devuelve 20 ruletas por página. Use ?pagina=N para navegar."
)
def listar_ruletas(
    pagina: int = Query(1, ge=1, description="Número de página (mínimo 1)"),
    solo_activas: bool = Query(False, description="Filtrar solo ruletas activas"),
    db: Session = Depends(get_db)
):
    """
    Lista todas las ruletas con paginación de 20 registros por página.
    Permite filtrar por ruletas activas mediante el parámetro solo_activas.
    """
    # Construir query base
    query = db.query(Ruleta)

    # Aplicar filtro opcional por estado activo
    if solo_activas:
        query = query.filter(Ruleta.activa == True)

    # Contar total de registros para calcular paginación
    total = query.count()
    paginas_totales = math.ceil(total / REGISTROS_POR_PAGINA) if total > 0 else 1

    # Validar que la página solicitada existe
    if pagina > paginas_totales and total > 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"La página {pagina} no existe. Total de páginas: {paginas_totales}"
        )

    # Calcular el desplazamiento (offset) para la paginación
    desplazamiento = (pagina - 1) * REGISTROS_POR_PAGINA

    # Obtener registros de la página actual, ordenados por fecha de creación
    ruletas = (
        query
        .order_by(Ruleta.created_at.desc())
        .offset(desplazamiento)
        .limit(REGISTROS_POR_PAGINA)
        .all()
    )

    return {
        "total": total,
        "pagina": pagina,
        "por_pagina": REGISTROS_POR_PAGINA,
        "paginas_totales": paginas_totales,
        "datos": ruletas
    }


# ─────────────────────────────────────────────
# ENDPOINT 3: CONSULTAR RULETA POR ID
# GET /ruletas/{ruleta_id}
# ─────────────────────────────────────────────
@router.get(
    "/{ruleta_id}",
    response_model=RuletaResponse,
    summary="Consultar ruleta por ID",
    description="Retorna los detalles completos de una ruleta específica."
)
def obtener_ruleta(
    ruleta_id: int,
    db: Session = Depends(get_db)
):
    """
    Busca y retorna una ruleta por su ID único.
    Devuelve 404 si no existe.
    """
    # Buscar la ruleta en la base de datos
    ruleta = db.query(Ruleta).filter(Ruleta.id == ruleta_id).first()

    # Si no existe, devolver error 404
    if not ruleta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró la ruleta con ID {ruleta_id}."
        )

    return ruleta


# ─────────────────────────────────────────────
# ENDPOINT 4: EDITAR RULETA
# PATCH /ruletas/{ruleta_id}
# ─────────────────────────────────────────────
@router.patch(
    "/{ruleta_id}",
    response_model=RuletaResponse,
    summary="Editar ruleta",
    description="Actualiza uno o más campos de una ruleta existente."
)
def editar_ruleta(
    ruleta_id: int,
    datos: RuletaUpdate,
    db: Session = Depends(get_db)
):
    """
    Actualización parcial de una ruleta.
    Solo se modifican los campos incluidos en el body de la petición.
    """
    # Buscar la ruleta a editar
    ruleta = db.query(Ruleta).filter(Ruleta.id == ruleta_id).first()

    if not ruleta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró la ruleta con ID {ruleta_id}."
        )

    # Obtener solo los campos que fueron enviados (excluir los None)
    campos_a_actualizar = datos.model_dump(exclude_unset=True)

    # Validar fechas si se están actualizando
    fecha_inicio = campos_a_actualizar.get("fecha_inicio", ruleta.fecha_inicio)
    fecha_cierre = campos_a_actualizar.get("fecha_cierre", ruleta.fecha_cierre)

    if fecha_cierre and fecha_cierre <= fecha_inicio:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La fecha de cierre debe ser posterior a la fecha de inicio."
        )

    # Aplicar cada campo modificado al objeto ORM
    for campo, valor in campos_a_actualizar.items():
        setattr(ruleta, campo, valor)

    db.commit()
    db.refresh(ruleta)

    return ruleta


# ─────────────────────────────────────────────
# ENDPOINT 5: ELIMINAR RULETA
# DELETE /ruletas/{ruleta_id}
# ─────────────────────────────────────────────
@router.delete(
    "/{ruleta_id}",
    status_code=status.HTTP_200_OK,
    summary="Eliminar ruleta",
    description="Elimina permanentemente una ruleta del sistema."
)
def eliminar_ruleta(
    ruleta_id: int,
    db: Session = Depends(get_db)
):
    """
    Elimina una ruleta por su ID.
    ADVERTENCIA: Esta acción es irreversible.
    Devuelve confirmación con el ID eliminado.
    """
    # Buscar la ruleta a eliminar
    ruleta = db.query(Ruleta).filter(Ruleta.id == ruleta_id).first()

    if not ruleta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró la ruleta con ID {ruleta_id}."
        )

    # Eliminar el registro de la base de datos
    db.delete(ruleta)
    db.commit()

    return {
        "mensaje": f"Ruleta con ID {ruleta_id} eliminada correctamente.",
        "id_eliminado": ruleta_id
    }
