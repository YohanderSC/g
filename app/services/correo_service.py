"""
=====================================================
SERVICIO DE CORREO - SISTEMA RULETA DE PREMIOS
=====================================================
Descripción: Lógica de negocio para el envío de correos.
             - Envío individual
             - Envío masivo en lotes de 500 (requerimiento #5)
             - Registro de cada envío en correos_log
             - Reenvío individual (requerimiento #10)

Tipos de correo:
  invitacion   → Se envía al importar clientes (con token)
  felicitacion → Se envía al ganador tras girar la ruleta
  referido     → Se envía cuando se aprueba un referido
  reenvio      → Reenvío manual de cualquier correo anterior
=====================================================
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models.models import Cliente, CorreoLog, TipoCorreo, EstadoCorreo, EstatusCliente
from app.config import settings


# ─────────────────────────────────────────────────────────
# PLANTILLAS DE CORREO (HTML)
# En Semana 3 estas plantillas se conectarán con los
# templates HTML de la maquetación de la ruleta.
# ─────────────────────────────────────────────────────────

def _plantilla_invitacion(cliente: Cliente) -> tuple[str, str]:
    """Retorna (asunto, cuerpo_html) para el correo de invitación."""
    asunto = "¡Tu invitación a la Ruleta de Premios!"
    cuerpo = f"""
    <html><body>
    <h2>¡Hola {cliente.nombres or cliente.email}!</h2>
    <p>Has sido invitado a participar en nuestra <strong>Ruleta de Premios</strong>.</p>
    <p>Tu código de acceso único es:</p>
    <h1 style="color:#e63946; letter-spacing:4px;">{cliente.token}</h1>
    <p>Ingresa con este código en nuestro sitio para girar la ruleta y ganar premios.</p>
    <p>¡Buena suerte!</p>
    </body></html>
    """
    return asunto, cuerpo


def _plantilla_felicitacion(cliente: Cliente, nombre_premio: str) -> tuple[str, str]:
    """Retorna (asunto, cuerpo_html) para el correo de felicitación al ganador."""
    asunto = f"¡Felicitaciones! Ganaste: {nombre_premio}"
    cuerpo = f"""
    <html><body>
    <h2>¡Felicitaciones {cliente.nombres or cliente.email}!</h2>
    <p>Giraste la ruleta y ganaste:</p>
    <h1 style="color:#2a9d8f;">{nombre_premio}</h1>
    <p>Comunícate con nosotros para coordinar la entrega de tu premio.</p>
    </body></html>
    """
    return asunto, cuerpo


def _plantilla_referido(cliente: Cliente, referidor_nombre: str) -> tuple[str, str]:
    """Retorna (asunto, cuerpo_html) para correo de referido aprobado."""
    asunto = f"{referidor_nombre} te invita a la Ruleta de Premios"
    cuerpo = f"""
    <html><body>
    <h2>¡Hola {cliente.nombres or cliente.email}!</h2>
    <p><strong>{referidor_nombre}</strong> te ha referido para participar en nuestra Ruleta de Premios.</p>
    <p>Tu código de acceso es:</p>
    <h1 style="color:#e63946; letter-spacing:4px;">{cliente.token}</h1>
    </body></html>
    """
    return asunto, cuerpo


# ─────────────────────────────────────────────────────────
# FUNCIÓN AUXILIAR: Registrar correo en el log
# ─────────────────────────────────────────────────────────

def _registrar_log(
    db:         Session,
    cliente_id: int,
    tipo:       TipoCorreo,
    estado:     EstadoCorreo,
    asunto:     str,
    lote_id:    Optional[str] = None,
    error_msg:  Optional[str] = None,
) -> CorreoLog:
    log = CorreoLog(
        cliente_id = cliente_id,
        tipo       = tipo,
        estado     = estado,
        asunto     = asunto,
        lote_id    = lote_id,
        error_msg  = error_msg,
        fecha_envio = datetime.utcnow(),
    )
    db.add(log)
    db.flush()
    return log


# ─────────────────────────────────────────────────────────
# FUNCIÓN PRINCIPAL: Enviar correo individual
# ─────────────────────────────────────────────────────────

async def enviar_correo_individual(
    db:           Session,
    cliente:      Cliente,
    tipo:         TipoCorreo,
    nombre_premio: Optional[str] = None,
    referidor:    Optional[str]  = None,
) -> dict:
    """
    Envía un correo a un cliente y lo registra en correos_log.
    Retorna un dict con el resultado del envío.
    """
    # Seleccionar plantilla según el tipo
    if tipo == TipoCorreo.invitacion:
        asunto, cuerpo = _plantilla_invitacion(cliente)
    elif tipo == TipoCorreo.felicitacion:
        asunto, cuerpo = _plantilla_felicitacion(cliente, nombre_premio or "Premio")
    elif tipo == TipoCorreo.referido:
        asunto, cuerpo = _plantilla_referido(cliente, referidor or "Un amigo")
    else:
        asunto, cuerpo = _plantilla_invitacion(cliente)   # reenvío usa invitación por defecto

    # Intentar envío real con fastapi-mail
    enviado = False
    error   = None

    try:
        from fastapi_mail import FastMail, MessageSchema, ConnectionConfig

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
            recipients = [cliente.email],
            body       = cuerpo,
            subtype    = "html",
        )

        fm = FastMail(config_mail)
        await fm.send_message(mensaje)
        enviado = True

    except Exception as e:
        error = str(e)

    # Registrar en log
    estado = EstadoCorreo.enviado if enviado else EstadoCorreo.fallido
    _registrar_log(db, cliente.id, tipo, estado, asunto, error_msg=error)
    db.commit()

    return {
        "cliente_id": cliente.id,
        "email":      cliente.email,
        "tipo":       tipo.value,
        "estado":     estado.value,
        "error":      error,
    }


# ─────────────────────────────────────────────────────────
# FUNCIÓN PRINCIPAL: Envío masivo en lotes de 500
# Requerimiento #5: envío masivo a clientes en lotes
# ─────────────────────────────────────────────────────────

async def enviar_masivo_invitacion(
    db:        Session,
    clientes:  list[Cliente],
    lote_size: int = 500,
) -> dict:
    """
    Envía correos de invitación a una lista de clientes en lotes de 500.
    Genera un lote_id único por lote para rastreo.

    Args:
        db:        Sesión de base de datos
        clientes:  Lista de clientes a quienes enviar
        lote_size: Tamaño máximo de cada lote (por defecto 500 según requerimiento)

    Returns:
        Resumen: total, enviados, fallidos, lotes procesados
    """
    total     = len(clientes)
    enviados  = 0
    fallidos  = 0
    lotes     = []

    # Dividir la lista en lotes de `lote_size`
    for i in range(0, total, lote_size):
        lote     = clientes[i:i + lote_size]
        lote_id  = str(uuid.uuid4())[:8]   # ID corto para identificar el lote en el log
        lote_ok  = 0
        lote_err = 0

        for cliente in lote:
            resultado = await enviar_correo_individual(
                db, cliente, TipoCorreo.invitacion
            )
            # Actualizar el lote_id del log recién creado
            ultimo_log = db.query(CorreoLog).filter(
                CorreoLog.cliente_id == cliente.id
            ).order_by(CorreoLog.id.desc()).first()
            if ultimo_log:
                ultimo_log.lote_id = lote_id
                db.flush()

            if resultado["estado"] == EstadoCorreo.enviado.value:
                lote_ok += 1
                enviados += 1
            else:
                lote_err += 1
                fallidos += 1

        db.commit()
        lotes.append({"lote_id": lote_id, "enviados": lote_ok, "fallidos": lote_err})

    return {
        "total":           total,
        "enviados":        enviados,
        "fallidos":        fallidos,
        "lotes_procesados": len(lotes),
        "detalle_lotes":   lotes,
    }


# ─────────────────────────────────────────────────────────
# FUNCIÓN: Reenvío individual (requerimiento #10)
# ─────────────────────────────────────────────────────────

async def reenviar_correo(db: Session, cliente_id: int) -> dict:
    """
    Reenvía el último correo enviado a un cliente.
    Registra el reenvío como tipo 'reenvio' en correos_log.
    """
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        return {"error": f"Cliente {cliente_id} no encontrado."}

    return await enviar_correo_individual(
        db, cliente, TipoCorreo.reenvio
    )
