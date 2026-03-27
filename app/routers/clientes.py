"""
=====================================================
ROUTER - CLIENTES (CRUD + IMPORTACIÓN MASIVA)
=====================================================
Endpoints:
  POST   /clientes/              → Crear cliente individual
  GET    /clientes/              → Listar (paginado, filtros)
  GET    /clientes/{id}          → Consultar por ID
  GET    /clientes/email/{email} → Consultar por email
  PATCH  /clientes/{id}          → Editar
  DELETE /clientes/{id}          → Eliminar
  POST   /clientes/importar/     → Importación masiva XLSX/CSV
=====================================================
"""
import secrets
import io
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import math

from app.database.database import get_db
from app.models.models import Cliente, EstatusCliente
from app.schemas.cliente_schema import (
    ClienteCreate, ClienteUpdate, ClienteResponse, ClienteListResponse,
    ImportacionResponse, ImportacionFila
)
from app.config import settings

router = APIRouter(prefix="/clientes", tags=["Clientes"])
POR_PAGINA = 20


def _generar_token() -> str:
    """Genera un token único seguro para el cliente (requerimiento #4)."""
    return secrets.token_urlsafe(settings.TOKEN_LENGTH)[:settings.TOKEN_LENGTH]


# ──────────────────────────────────────────────────────
# ENDPOINT 1: CREAR CLIENTE INDIVIDUAL
# ──────────────────────────────────────────────────────
@router.post("/", response_model=ClienteResponse, status_code=status.HTTP_201_CREATED,
             summary="Crear cliente individual")
def crear_cliente(datos: ClienteCreate, db: Session = Depends(get_db)):
    """
    Crea un cliente y genera automáticamente su token único.
    Lanza 409 si el email ya existe.
    """
    # Verificar email duplicado
    if db.query(Cliente).filter(Cliente.email == str(datos.email)).first():
        raise HTTPException(status_code=409,
                            detail=f"El email '{datos.email}' ya está registrado.")

    cliente = Cliente(
        **datos.model_dump(),
        token=_generar_token(),
        estatus=EstatusCliente.anadido
    )
    db.add(cliente)
    db.commit()
    db.refresh(cliente)
    return cliente


# ──────────────────────────────────────────────────────
# ENDPOINT 2: LISTAR CLIENTES CON FILTROS
# ──────────────────────────────────────────────────────
@router.get("/", response_model=ClienteListResponse, summary="Listar clientes paginados")
def listar_clientes(
    pagina:     int            = Query(1, ge=1),
    agencia_id: int | None     = Query(None, description="Filtrar por agencia"),
    estatus:    str | None     = Query(None, description="Filtrar por estatus"),
    buscar:     str | None     = Query(None, description="Buscar por nombre o email"),
    db: Session = Depends(get_db)
):
    query = db.query(Cliente)

    if agencia_id:
        query = query.filter(Cliente.agencia_id == agencia_id)
    if estatus:
        try:
            estatus_enum = EstatusCliente(estatus)
            query = query.filter(Cliente.estatus == estatus_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Estatus '{estatus}' no válido.")
    if buscar:
        like = f"%{buscar}%"
        query = query.filter(
            (Cliente.email.ilike(like)) |
            (Cliente.nombres.ilike(like)) |
            (Cliente.apellidos.ilike(like))
        )

    total           = query.count()
    paginas_totales = math.ceil(total / POR_PAGINA) if total > 0 else 1
    datos           = query.order_by(Cliente.created_at.desc()).offset((pagina - 1) * POR_PAGINA).limit(POR_PAGINA).all()

    return {"total": total, "pagina": pagina, "por_pagina": POR_PAGINA,
            "paginas_totales": paginas_totales, "datos": datos}


# ──────────────────────────────────────────────────────
# ENDPOINT 3: CONSULTAR POR ID
# ──────────────────────────────────────────────────────
@router.get("/{cliente_id}", response_model=ClienteResponse, summary="Consultar cliente por ID")
def obtener_cliente(cliente_id: int, db: Session = Depends(get_db)):
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail=f"Cliente {cliente_id} no encontrado.")
    return cliente


# ──────────────────────────────────────────────────────
# ENDPOINT 4: CONSULTAR POR EMAIL
# ──────────────────────────────────────────────────────
@router.get("/email/{email}", response_model=ClienteResponse, summary="Consultar cliente por email")
def obtener_cliente_por_email(email: str, db: Session = Depends(get_db)):
    cliente = db.query(Cliente).filter(Cliente.email == email).first()
    if not cliente:
        raise HTTPException(status_code=404, detail=f"Cliente con email '{email}' no encontrado.")
    return cliente


# ──────────────────────────────────────────────────────
# ENDPOINT 5: EDITAR CLIENTE
# ──────────────────────────────────────────────────────
@router.patch("/{cliente_id}", response_model=ClienteResponse, summary="Editar cliente")
def editar_cliente(cliente_id: int, datos: ClienteUpdate, db: Session = Depends(get_db)):
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail=f"Cliente {cliente_id} no encontrado.")

    for campo, valor in datos.model_dump(exclude_unset=True).items():
        setattr(cliente, campo, valor)

    db.commit()
    db.refresh(cliente)
    return cliente


# ──────────────────────────────────────────────────────
# ENDPOINT 6: ELIMINAR CLIENTE
# ──────────────────────────────────────────────────────
@router.delete("/{cliente_id}", status_code=status.HTTP_200_OK,
               summary="Eliminar cliente")
def eliminar_cliente(cliente_id: int, db: Session = Depends(get_db)):
    """
    Elimina un cliente. Si tiene registros relacionados
    (participaciones, correos, etc.) devuelve error descriptivo.
    """
    from sqlalchemy.exc import IntegrityError

    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404,
                            detail=f"Cliente {cliente_id} no encontrado.")

    try:
        db.delete(cliente)
        db.commit()
        return {"mensaje": f"Cliente {cliente_id} eliminado.", "id_eliminado": cliente_id}

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"No se puede eliminar el cliente '{cliente.email}' porque tiene "
                "registros relacionados (participaciones, correos, etc.). "
                "Elimina primero esos registros o desactiva el cliente en lugar de eliminarlo."
            )
        )
# ──────────────────────────────────────────────────────
# ENDPOINT 7: IMPORTACIÓN MASIVA XLSX / CSV
# POST /clientes/importar/
# Requerimiento #1: migración masiva desde archivo
# ──────────────────────────────────────────────────────
@router.post("/importar/", response_model=ImportacionResponse,
             status_code=status.HTTP_200_OK,
             summary="Importar clientes masivamente desde XLSX o CSV")
async def importar_clientes(
    archivo: UploadFile = File(..., description="Archivo .xlsx o .csv con columnas: email, nombres, apellidos, celular, agencia_id"),
    db: Session = Depends(get_db)
):
    """
    Importa clientes desde un archivo XLSX o CSV.

    **Columnas esperadas en el archivo:**
    - `email` (obligatorio) — identificador único del cliente
    - `nombres` (opcional)
    - `apellidos` (opcional)
    - `celular` (opcional)
    - `agencia_id` (opcional)

    **Reglas de importación:**
    - Si el email ya existe → se marca como `duplicado` (no se actualiza)
    - Si falta el email o es inválido → se marca como `error`
    - Cada cliente importado recibe un token único automáticamente
    """
    import pandas as pd

    # Validar tipo de archivo
    nombre = archivo.filename or ""
    if not (nombre.endswith(".xlsx") or nombre.endswith(".csv")):
        raise HTTPException(status_code=400,
                            detail="Solo se aceptan archivos .xlsx o .csv")

    # Leer el archivo en memoria
    contenido = await archivo.read()

    try:
        if nombre.endswith(".xlsx"):
            df = pd.read_excel(io.BytesIO(contenido), dtype=str)
        else:
            df = pd.read_csv(io.BytesIO(contenido), dtype=str)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al leer el archivo: {str(e)}")

    # Normalizar nombres de columnas (minúsculas, sin espacios)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    if "email" not in df.columns:
        raise HTTPException(status_code=400,
                            detail="El archivo debe tener una columna 'email'.")

    # ── Procesar fila por fila ─────────────────────
    importados = 0
    duplicados = 0
    errores    = 0
    detalle: list[ImportacionFila] = []

    for idx, fila in df.iterrows():
        num_fila = int(idx) + 2   # +2 porque idx=0 es la fila 2 del excel (fila 1 es el header)
        email    = str(fila.get("email", "")).strip()

        # Validar email
        if not email or "@" not in email:
            errores += 1
            detalle.append(ImportacionFila(
                fila=num_fila, email=email or "(vacío)",
                estado="error", detalle="Email vacío o inválido"
            ))
            continue

        # Verificar duplicado en BD
        if db.query(Cliente).filter(Cliente.email == email).first():
            duplicados += 1
            detalle.append(ImportacionFila(
                fila=num_fila, email=email,
                nombres=str(fila.get("nombres", "")) or None,
                estado="duplicado", detalle="Email ya registrado"
            ))
            continue

        # Construir objeto cliente
        try:
            agencia_id_val = fila.get("agencia_id")
            agencia_id = int(agencia_id_val) if pd.notna(agencia_id_val) and str(agencia_id_val).strip() else None

            cliente = Cliente(
                email     = email,
                nombres   = str(fila.get("nombres",   "")).strip() or None,
                apellidos = str(fila.get("apellidos", "")).strip() or None,
                celular   = str(fila.get("celular",   "")).strip() or None,
                agencia_id = agencia_id,
                token     = _generar_token(),
                estatus   = EstatusCliente.anadido,
            )
            db.add(cliente)
            db.flush()   # Detectar errores de integridad antes del commit final

            importados += 1
            detalle.append(ImportacionFila(
                fila=num_fila, email=email,
                nombres=cliente.nombres,
                estado="importado"
            ))

        except IntegrityError:
            db.rollback()
            duplicados += 1
            detalle.append(ImportacionFila(
                fila=num_fila, email=email,
                estado="duplicado", detalle="Email duplicado detectado al guardar"
            ))
        except Exception as e:
            errores += 1
            detalle.append(ImportacionFila(
                fila=num_fila, email=email,
                estado="error", detalle=str(e)
            ))

    # Confirmar todos los clientes importados de una vez
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al guardar en BD: {str(e)}")

    return ImportacionResponse(
        archivo     = nombre,
        total_filas = len(df),
        importados  = importados,
        duplicados  = duplicados,
        errores     = errores,
        detalle     = detalle
    )
