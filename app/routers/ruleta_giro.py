"""
=====================================================
ROUTER - GIRO DE RULETA Y REPORTES
=====================================================
Endpoints:
  POST  /ruleta/girar/              → Girar la ruleta (Req. #4, #6, #7, #8)
  GET   /ruleta/validar/{token}     → Validar token antes de mostrar ruleta
  GET   /ruleta/reporte/{ruleta_id} → Estadísticas de participación (Req. #11)
  GET   /ruleta/ganadores/{ruleta_id} → Listado de ganadores
  POST  /correos/masivo/            → Envío masivo de invitaciones (Req. #5)
  POST  /correos/reenviar/{id}      → Reenvío individual (Req. #10)
=====================================================
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.models import Cliente, CorreoLog
from app.schemas.giro_schema import GiroRequest, GiroResponse
from app.services import giro_service

router = APIRouter(tags=["Ruleta - Giro y Reportes"])


# ─────────────────────────────────────────────────────────
# ENDPOINT 1: GIRAR LA RULETA (Req. #4, #6, #7, #8)
# ─────────────────────────────────────────────────────────
@router.post(
    "/ruleta/girar/",
    response_model=GiroResponse,
    status_code=status.HTTP_200_OK,
    summary="Girar la ruleta",
    description="""
Ejecuta el giro completo de la ruleta para un cliente.

**Flujo:**
1. Valida el token del cliente (Req. #4)
2. Verifica si tiene premio condicionado (Req. #7)
3. Si no, asigna premio aleatorio ponderado (Req. #6)
4. Registra la participación
5. Genera correo de felicitación pendiente (Req. #8)
    """
)
def girar_ruleta(datos: GiroRequest, db: Session = Depends(get_db)):
    return giro_service.ejecutar_giro(db, datos.token, datos.ruleta_id)


# ─────────────────────────────────────────────────────────
# ENDPOINT 2: VALIDAR TOKEN (antes de mostrar la ruleta)
# ─────────────────────────────────────────────────────────
@router.get(
    "/ruleta/validar/{token}",
    summary="Validar token del cliente",
    description="Verifica el token y si el cliente ya participo en la ruleta indicada."
)
def validar_token(
    token:     str,
    ruleta_id: int | None = Query(None, description="ID de la ruleta a verificar"),
    db: Session = Depends(get_db)
):
    from app.models.models import Participacion

    # Solo verificar que el token existe — no importa si ya giro otras ruletas
    cliente = db.query(Cliente).filter(Cliente.token == token).first()

    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalido. Verifica tu codigo de acceso."
        )

    # Verificar si ya participo en ESTA ruleta especifica
    ya_participo = False
    participacion_previa = None
    if ruleta_id:
        p = db.query(Participacion).filter(
            Participacion.cliente_id == cliente.id,
            Participacion.ruleta_id  == ruleta_id,
        ).first()
        if p:
            ya_participo = True
            participacion_previa = {
                "premio":    p.premio.nombre if p.premio else "Sin premio",
                "fecha":     str(p.fecha_participacion),
                "entregado": p.premio_entregado,
            }

    return {
        "valido":              True,
        "ya_participo":        ya_participo,
        "participacion_previa": participacion_previa,
        "cliente": {
            "id":       cliente.id,
            "email":    cliente.email,
            "nombres":  cliente.nombres,
            "apellidos":cliente.apellidos,
        }
    }


# ─────────────────────────────────────────────────────────
# ENDPOINT 3: REPORTE DE PARTICIPACIÓN (Req. #11)
# ─────────────────────────────────────────────────────────
@router.get(
    "/ruleta/reporte/{ruleta_id}",
    summary="Estadísticas de participación",
    description="Retorna estadísticas globales y por agencia, más listado de ganadores."
)
def reporte_participacion(ruleta_id: int, db: Session = Depends(get_db)):
    return giro_service.obtener_estadisticas(db, ruleta_id)


# ─────────────────────────────────────────────────────────
# ENDPOINT 4: LISTADO DE GANADORES
# ─────────────────────────────────────────────────────────
@router.get(
    "/ruleta/ganadores/{ruleta_id}",
    summary="Listado de ganadores de una ruleta"
)
def listar_ganadores(ruleta_id: int, db: Session = Depends(get_db)):
    """
    Lista TODOS los participantes de una ruleta con o sin premio.
    Incluye ganadores condicionados y aleatorios.
    """
    from app.models.models import Participacion, Premio
    # Traer TODAS las participaciones de la ruleta (con y sin premio)
    participaciones = db.query(Participacion).filter(
        Participacion.ruleta_id == ruleta_id,
    ).order_by(Participacion.fecha_participacion.desc()).all()

    return {
        "ruleta_id": ruleta_id,
        "total":     len(participaciones),
        "ganadores": [{
            "participacion_id": g.id,
            "cliente_id":       g.cliente_id,
            "cliente_email":    g.cliente.email if g.cliente else "-",
            "cliente_nombre":   f"{g.cliente.nombres or ''} {g.cliente.apellidos or ''}".strip() if g.cliente else "-",
            "premio_id":        g.premio_id,
            "premio":           g.premio.nombre if g.premio else "Sin premio",
            "gano":             g.premio_id is not None,
            "entregado":        g.premio_entregado,
            "fecha":            str(g.fecha_participacion),
        } for g in participaciones]
    }


# Schema para los datos de entrega
from pydantic import BaseModel
from typing import Optional as Opt

class DatosEntrega(BaseModel):
    fecha_entrega: Opt[str] = None   # Ej: "Lunes 25 de marzo de 2026"
    hora_entrega:  Opt[str] = None   # Ej: "10:00 AM - 12:00 PM"
    lugar_entrega: Opt[str] = None   # Ej: "Oficina Central, Av. España 1234"
    notas_entrega: Opt[str] = None   # Ej: "Presentar cédula de identidad"
    enviar_correo: bool = True       # Si enviar correo de notificación


@router.patch(
    "/ruleta/ganadores/{participacion_id}/entregar",
    summary="Marcar premio como entregado y notificar al ganador",
    description="""
Registra la entrega física del premio y envía correo de notificación al ganador
con la fecha, hora y lugar de entrega.
    """
)
async def marcar_entregado(
    participacion_id: int,
    datos: DatosEntrega = DatosEntrega(),
    db: Session = Depends(get_db)
):
    from app.models.models import Participacion
    from app.services.correo_service import enviar_correo_individual
    from app.models.models import TipoCorreo

    p = db.query(Participacion).filter(Participacion.id == participacion_id).first()
    if not p:
        raise HTTPException(status_code=404, detail=f"Participación {participacion_id} no encontrada.")
    if not p.premio_id:
        raise HTTPException(status_code=400, detail="Esta participación no tiene premio asignado.")
    if p.premio_entregado:
        raise HTTPException(status_code=400, detail="El premio ya fue marcado como entregado.")

    # Marcar como entregado
    p.premio_entregado = True
    if p.premio:
        if p.premio.cantidad_entregada is None:
            p.premio.cantidad_entregada = 0
        p.premio.cantidad_entregada += 1

    db.commit()
    db.refresh(p)

    # Enviar correo de notificación con datos de entrega
    correo_enviado = False
    correo_error   = None

    if datos.enviar_correo and p.cliente:
        try:
            from app.services.correo_service import _plantilla_felicitacion
            from app.services.correo_service import _registrar_log
            from app.models.models import EstadoCorreo, CorreoLog
            from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
            from app.config import settings

            nombre_premio = p.premio.nombre if p.premio else "Premio"
            asunto, cuerpo = _plantilla_felicitacion(
                cliente       = p.cliente,
                nombre_premio = nombre_premio,
                fecha_entrega = datos.fecha_entrega,
                hora_entrega  = datos.hora_entrega,
                lugar_entrega = datos.lugar_entrega,
                notas_entrega = datos.notas_entrega,
            )

            config_mail = ConnectionConfig(
                MAIL_USERNAME   = settings.MAIL_USERNAME,
                MAIL_PASSWORD   = settings.MAIL_PASSWORD,
                MAIL_FROM       = settings.MAIL_FROM,
                MAIL_FROM_NAME  = settings.MAIL_FROM_NAME,
                MAIL_PORT       = settings.MAIL_PORT,
                MAIL_SERVER     = settings.MAIL_SERVER,
                MAIL_STARTTLS   = settings.MAIL_TLS,
                MAIL_SSL_TLS    = settings.MAIL_SSL,
                USE_CREDENTIALS = True,
            )
            mensaje = MessageSchema(
                subject    = asunto,
                recipients = [p.cliente.email],
                body       = cuerpo,
                subtype    = "html",
            )
            await FastMail(config_mail).send_message(mensaje)
            correo_enviado = True

            # Registrar en log
            log = CorreoLog(
                cliente_id  = p.cliente.id,
                tipo        = TipoCorreo.felicitacion,
                estado      = EstadoCorreo.enviado,
                asunto      = asunto,
            )
            db.add(log)
            db.commit()

        except Exception as e:
            correo_error = str(e)

    return {
        "participacion_id": p.id,
        "cliente_email":    p.cliente.email if p.cliente else "-",
        "cliente_nombre":   f"{p.cliente.nombres or ''} {p.cliente.apellidos or ''}".strip() if p.cliente else "-",
        "premio":           p.premio.nombre if p.premio else "-",
        "entregado":        True,
        "correo_enviado":   correo_enviado,
        "correo_error":     correo_error,
        "datos_entrega": {
            "fecha":  datos.fecha_entrega,
            "hora":   datos.hora_entrega,
            "lugar":  datos.lugar_entrega,
            "notas":  datos.notas_entrega,
        },
        "mensaje": "Premio marcado como entregado ✅" + (" — Correo enviado 📧" if correo_enviado else "")
    }


# ─────────────────────────────────────────────────────────
# ENDPOINT 5: ENVÍO MASIVO DE INVITACIONES (Req. #5)
# ─────────────────────────────────────────────────────────
@router.post(
    "/correos/masivo/",
    summary="Envío masivo de invitaciones (lotes de 500)",
    description="Envía correos de invitación con token a todos los clientes en estatus 'anadido'. Se procesa en lotes de 500."
)
async def enviar_masivo(db: Session = Depends(get_db)):
    from app.models.models import EstatusCliente
    from app.services.correo_service import enviar_masivo_invitacion

    clientes = db.query(Cliente).filter(
        Cliente.estatus == EstatusCliente.anadido,
        Cliente.token   != None,
    ).all()

    if not clientes:
        return {"mensaje": "No hay clientes pendientes de invitación.", "total": 0}

    resultado = await enviar_masivo_invitacion(db, clientes)
    return resultado


# ─────────────────────────────────────────────────────────
# ENDPOINT 6: REENVÍO INDIVIDUAL (Req. #10)
# ─────────────────────────────────────────────────────────
@router.post(
    "/correos/reenviar/{cliente_id}",
    summary="Reenviar correo a cliente específico (Req. #10)",
    description="Reenvía el correo de invitación a un cliente específico. Registra el reenvío en correos_log."
)
async def reenviar_correo(cliente_id: int, db: Session = Depends(get_db)):
    from app.services.correo_service import reenviar_correo as svc_reenviar

    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail=f"Cliente {cliente_id} no encontrado.")

    resultado = await svc_reenviar(db, cliente_id)
    return resultado


@router.post(
    "/correos/reenviar/email/",
    summary="Reenviar correo por email (más fácil para admins)",
    description="Reenvía el correo de invitación usando el email del cliente. Más fácil que buscar el ID."
)
async def reenviar_por_email(
    email: str = Query(..., description="Email del cliente"),
    db: Session = Depends(get_db)
):
    from app.services.correo_service import reenviar_correo as svc_reenviar

    email_limpio = email.strip().lower()
    cliente = db.query(Cliente).filter(Cliente.email == email_limpio).first()

    if not cliente:
        raise HTTPException(
            status_code=404,
            detail=f"No se encontró ningún cliente con el email '{email}'."
        )

    resultado = await svc_reenviar(db, cliente.id)
    return {
        **resultado,
        "email": cliente.email,
    }


# ─────────────────────────────────────────────────────────
# ENDPOINT 7: HISTORIAL DE CORREOS DE UN CLIENTE
# ─────────────────────────────────────────────────────────
@router.get(
    "/correos/historial/{cliente_id}",
    summary="Historial de correos de un cliente"
)
def historial_correos(cliente_id: int, db: Session = Depends(get_db)):
    logs = db.query(CorreoLog).filter(
        CorreoLog.cliente_id == cliente_id
    ).order_by(CorreoLog.fecha_envio.desc()).all()

    return {
        "cliente_id": cliente_id,
        "total":      len(logs),
        "historial":  [{
            "id":        l.id,
            "tipo":      l.tipo.value,
            "estado":    l.estado.value,
            "asunto":    l.asunto,
            "fecha":     str(l.fecha_envio),
            "lote_id":   l.lote_id,
            "error_msg": l.error_msg,
        } for l in logs]
    }
