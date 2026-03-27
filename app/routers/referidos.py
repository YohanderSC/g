"""
=====================================================
ROUTER - REFERIDOS
=====================================================
Endpoints para clientes:
  POST  /referidos/              → Crear solicitud de referido
  GET   /referidos/mis/{token}   → Ver mis referidos enviados

Endpoints para admin:
  GET   /referidos/              → Listar todas las solicitudes (con filtros)
  GET   /referidos/{id}          → Ver detalle de una solicitud
  PATCH /referidos/{id}/aprobar  → Aprobar → crea cliente + envía correo (Req. #9)
  PATCH /referidos/{id}/rechazar → Rechazar solicitud
=====================================================
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.services import referido_service

router = APIRouter(prefix="/referidos", tags=["Referidos"])


# ── CLIENTE: Crear solicitud ──────────────────────
@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    summary="Crear solicitud de referido",
    description="""
El cliente que participó puede referir a otra persona.
Se identifica con su token. El referido recibirá un correo
con su propio token cuando el admin apruebe la solicitud.
    """
)
def crear_referido(
    token_referidor:  str       = Query(..., description="Token del cliente que refiere"),
    email_referido:   str       = Query(..., description="Email de la persona a referir"),
    nombres_referido: str | None = Query(None, description="Nombre del referido (opcional)"),
    ruleta_id:        int       = Query(..., description="ID de la ruleta"),
    db: Session = Depends(get_db)
):
    return referido_service.crear_referido(
        db, token_referidor, email_referido, nombres_referido, ruleta_id
    )


# ── ADMIN: Listar solicitudes ─────────────────────
@router.get(
    "/",
    summary="Listar solicitudes de referido (Admin)",
    description="Muestra todas las solicitudes. Filtrar por estatus: pendiente, aprobado, rechazado."
)
def listar_referidos(
    pagina:  int       = Query(1, ge=1),
    estatus: str | None = Query(None, description="pendiente | aprobado | rechazado"),
    db: Session = Depends(get_db)
):
    return referido_service.listar_referidos(db, pagina, estatus)


# ── ADMIN: Ver detalle ────────────────────────────
@router.get("/{solicitud_id}", summary="Ver detalle de una solicitud")
def ver_referido(solicitud_id: int, db: Session = Depends(get_db)):
    from app.models.referido_model_orm import SolicitudReferido
    s = db.query(SolicitudReferido).filter(SolicitudReferido.id == solicitud_id).first()
    if not s:
        raise HTTPException(status_code=404, detail=f"Solicitud {solicitud_id} no encontrada.")
    return referido_service._serializar(s, db)


# ── ADMIN: Aprobar ────────────────────────────────
@router.patch(
    "/{solicitud_id}/aprobar",
    summary="Aprobar solicitud de referido (Admin)",
    description="""
Al aprobar:
1. Se crea el cliente referido con token único
2. Se actualiza el estatus del referidor
3. Se envía correo al referido con su token de acceso (Req. #9)
    """
)
async def aprobar_referido(solicitud_id: int, db: Session = Depends(get_db)):
    return await referido_service.aprobar_referido(db, solicitud_id)


# ── ADMIN: Rechazar ───────────────────────────────
@router.patch(
    "/{solicitud_id}/rechazar",
    summary="Rechazar solicitud de referido (Admin)"
)
def rechazar_referido(
    solicitud_id: int,
    motivo: str | None = Query(None, description="Motivo del rechazo (opcional)"),
    db: Session = Depends(get_db)
):
    return referido_service.rechazar_referido(db, solicitud_id, motivo)


# ── CLIENTE: Ver mis referidos enviados ───────────
@router.get(
    "/mis/{token}",
    summary="Ver mis referidos (por token del cliente)"
)
def mis_referidos(token: str, db: Session = Depends(get_db)):
    from app.models.models import Cliente
    from app.models.referido_model_orm import SolicitudReferido

    cliente = db.query(Cliente).filter(Cliente.token == token).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Token no encontrado.")

    solicitudes = db.query(SolicitudReferido).filter(
        SolicitudReferido.referidor_id == cliente.id
    ).order_by(SolicitudReferido.fecha_solicitud.desc()).all()

    return {
        "cliente_id":   cliente.id,
        "email":        cliente.email,
        "total":        len(solicitudes),
        "referidos":    [referido_service._serializar(s, db) for s in solicitudes],
    }
