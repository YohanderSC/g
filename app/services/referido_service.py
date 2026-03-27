"""
=====================================================
SERVICIO DE REFERIDOS - SISTEMA RULETA DE PREMIOS
=====================================================
Flujo completo:

  CLIENTE:
    1. Después de girar, el cliente puede referir a alguien
    2. POST /referidos/ con su token + email del referido
    3. Se crea una SolicitudReferido con estatus "pendiente"

  ADMIN:
    4. Ve las solicitudes pendientes en el panel
    5. PATCH /referidos/{id}/aprobar
       → Crea el cliente referido con token único
       → Actualiza estatus del referidor a "referido_aprobado"
       → Envía correo al referido con su token (Req. #9)
    6. PATCH /referidos/{id}/rechazar
       → Marca como rechazado, sin crear cliente

Requerimiento cubierto:
  #9 — Notificación vía correo de referidos aprobados
=====================================================
"""
import secrets
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.models import (
    Cliente, Ruleta, EstatusCliente, CorreoLog, TipoCorreo, EstadoCorreo
)


# ─────────────────────────────────────────────────
# FUNCIÓN: Crear solicitud de referido
# ─────────────────────────────────────────────────
def crear_referido(db: Session, token_referidor: str, email_referido: str,
                   nombres_referido: str | None, ruleta_id: int) -> dict:
    """
    Un cliente registra una solicitud para referir a otra persona.
    El referidor se identifica por su token.
    """
    from app.models.referido_model_orm import SolicitudReferido, EstatusReferido

    # 1. Validar que el referidor existe (por token)
    referidor = db.query(Cliente).filter(Cliente.token == token_referidor).first()
    if not referidor:
        raise HTTPException(status_code=401, detail="Token del referidor inválido.")

    # 2. Validar que la ruleta existe y está activa
    ruleta = db.query(Ruleta).filter(Ruleta.id == ruleta_id, Ruleta.activa == True).first()
    if not ruleta:
        raise HTTPException(status_code=404, detail=f"Ruleta {ruleta_id} no encontrada o inactiva.")

    # 3. Evitar auto-referido
    if email_referido.lower() == referidor.email.lower():
        raise HTTPException(status_code=400, detail="No puedes referirte a ti mismo.")

    # 4. Verificar que el email referido no está ya registrado
    ya_existe = db.query(Cliente).filter(Cliente.email == email_referido).first()
    if ya_existe:
        raise HTTPException(status_code=409,
                            detail=f"El email '{email_referido}' ya está registrado en el sistema.")

    # 5. Verificar que no existe ya una solicitud pendiente para ese email/ruleta
    from app.models.referido_model_orm import SolicitudReferido
    solicitud_previa = db.query(SolicitudReferido).filter(
        SolicitudReferido.email_referido == email_referido,
        SolicitudReferido.ruleta_id      == ruleta_id,
        SolicitudReferido.estatus        == EstatusReferido.pendiente,
    ).first()
    if solicitud_previa:
        raise HTTPException(status_code=409,
                            detail="Ya existe una solicitud pendiente para ese email en esta ruleta.")

    # 6. Crear la solicitud
    solicitud = SolicitudReferido(
        referidor_id     = referidor.id,
        email_referido   = email_referido.lower(),
        nombres_referido = nombres_referido,
        ruleta_id        = ruleta_id,
        estatus          = EstatusReferido.pendiente,
    )
    db.add(solicitud)
    db.commit()
    db.refresh(solicitud)

    return _serializar(solicitud, db)


# ─────────────────────────────────────────────────
# FUNCIÓN: Aprobar solicitud de referido (Admin)
# ─────────────────────────────────────────────────
async def aprobar_referido(db: Session, solicitud_id: int) -> dict:
    """
    Admin aprueba la solicitud:
    - Crea el cliente referido con token único
    - Actualiza el referidor a estatus referido_aprobado
    - Envía correo al referido con su token (Req. #9)
    """
    from app.models.referido_model_orm import SolicitudReferido, EstatusReferido
    from app.services.correo_service import enviar_correo_individual

    solicitud = db.query(SolicitudReferido).filter(
        SolicitudReferido.id == solicitud_id
    ).first()
    if not solicitud:
        raise HTTPException(status_code=404, detail=f"Solicitud {solicitud_id} no encontrada.")
    if solicitud.estatus != EstatusReferido.pendiente:
        raise HTTPException(status_code=400,
                            detail=f"La solicitud ya fue procesada (estatus: {solicitud.estatus.value}).")

    # Verificar de nuevo que el email no fue registrado mientras tanto
    ya_existe = db.query(Cliente).filter(Cliente.email == solicitud.email_referido).first()
    if ya_existe:
        solicitud.estatus          = EstatusReferido.rechazado
        solicitud.fecha_resolucion = datetime.utcnow()
        db.commit()
        raise HTTPException(status_code=409,
                            detail="El email del referido ya fue registrado. Solicitud rechazada automáticamente.")

    # Crear el cliente referido
    token = secrets.token_urlsafe(32)[:32]
    cliente_referido = Cliente(
        email            = solicitud.email_referido,
        nombres          = solicitud.nombres_referido,
        agencia_id       = solicitud.referidor.agencia_id,   # Misma agencia que el referidor
        token            = token,
        estatus          = EstatusCliente.referido_aprobado,
        referido_por_id  = solicitud.referidor_id,
    )
    db.add(cliente_referido)
    db.flush()   # Para obtener el ID

    # Actualizar la solicitud
    solicitud.cliente_id       = cliente_referido.id
    solicitud.estatus          = EstatusReferido.aprobado
    solicitud.fecha_resolucion = datetime.utcnow()

    # Actualizar estatus del referidor
    referidor = solicitud.referidor
    if referidor.estatus == EstatusCliente.participo:
        referidor.estatus = EstatusCliente.referido_aprobado

    db.commit()
    db.refresh(cliente_referido)

    # Nombre del referidor para el correo
    nombre_referidor = " ".join(filter(None, [referidor.nombres, referidor.apellidos])) \
                       or referidor.email

    # Enviar correo al referido (Req. #9)
    await enviar_correo_individual(
        db        = db,
        cliente   = cliente_referido,
        tipo      = TipoCorreo.referido,
        referidor = nombre_referidor,
    )

    return {
        **_serializar(solicitud, db),
        "cliente_creado": {
            "id":    cliente_referido.id,
            "email": cliente_referido.email,
            "token": cliente_referido.token,
        },
        "correo_enviado": True,
    }


# ─────────────────────────────────────────────────
# FUNCIÓN: Rechazar solicitud
# ─────────────────────────────────────────────────
async def rechazar_referido(db: Session, solicitud_id: int, motivo: str | None = None) -> dict:
    from app.models.referido_model_orm import SolicitudReferido, EstatusReferido

    solicitud = db.query(SolicitudReferido).filter(
        SolicitudReferido.id == solicitud_id
    ).first()
    if not solicitud:
        raise HTTPException(status_code=404, detail=f"Solicitud {solicitud_id} no encontrada.")
    if solicitud.estatus != EstatusReferido.pendiente:
        raise HTTPException(status_code=400,
                            detail=f"La solicitud ya fue procesada (estatus: {solicitud.estatus.value}).")

    motivo_final = motivo or "No cumple los requisitos para participar en esta oportunidad."
    solicitud.estatus          = EstatusReferido.rechazado
    solicitud.motivo_rechazo   = motivo_final
    solicitud.fecha_resolucion = datetime.utcnow()
    db.commit()

    # Notificar al referidor por correo
    try:
        from app.models.models import CorreoLog, TipoCorreo, EstadoCorreo
        from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
        from app.config import settings

        referidor  = solicitud.referidor
        if referidor:
            nombre_ref = referidor.nombres or referidor.email.split("@")[0]
            nombre_inv = solicitud.nombres_referido or solicitud.email_referido

            asunto = f"Actualizacion sobre tu referido - {nombre_inv}"
            cuerpo = f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#0D0D14;font-family:'Segoe UI',Arial,sans-serif">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0D0D14;padding:40px 20px">
    <tr><td align="center">
      <table width="100%" style="max-width:520px;background:#12121A;border-radius:20px;overflow:hidden;border:1px solid rgba(255,255,255,0.08)">
        <tr><td style="background:#1C1C28;padding:28px 32px;border-bottom:1px solid rgba(255,255,255,0.06)">
          <div style="font-size:.7rem;letter-spacing:3px;text-transform:uppercase;color:rgba(240,237,232,.4);margin-bottom:8px">Notificacion de referido</div>
          <h2 style="margin:0;color:#F0EDE8;font-size:1.3rem;font-weight:700">Actualizacion sobre tu referido</h2>
        </td></tr>
        <tr><td style="padding:32px">
          <p style="color:#F0EDE8;font-size:1rem;margin:0 0 14px">Hola, <strong style="color:#D4AF37">{nombre_ref}</strong></p>
          <p style="color:rgba(240,237,232,.65);font-size:.9rem;line-height:1.7;margin:0 0 22px">
            Gracias por referir a <strong style="color:#F0EDE8">{nombre_inv}</strong>.<br>
            Lamentablemente, la solicitud no pudo ser aprobada en esta oportunidad.
          </p>
          <div style="background:#1C1C28;border:1px solid rgba(231,76,60,.2);border-left:3px solid #E74C3C;border-radius:10px;padding:16px 18px;margin-bottom:22px">
            <div style="font-size:.68rem;letter-spacing:2px;text-transform:uppercase;color:rgba(231,76,60,.7);margin-bottom:6px">Motivo del rechazo</div>
            <div style="color:#F0EDE8;font-size:.9rem;line-height:1.5">{motivo_final}</div>
          </div>
          <p style="color:rgba(240,237,232,.45);font-size:.82rem;line-height:1.6;margin:0">
            Si tienes dudas, comunicate con nosotros respondiendo este correo.
          </p>
        </td></tr>
        <tr><td style="background:#0A0A0F;padding:16px 32px;border-top:1px solid rgba(255,255,255,.06)">
          <p style="color:rgba(240,237,232,.2);font-size:.72rem;text-align:center;margin:0">
            2026 Ruleta de Premios
          </p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body></html>"""

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
            await FastMail(config_mail).send_message(MessageSchema(
                subject    = asunto,
                recipients = [referidor.email],
                body       = cuerpo,
                subtype    = "html",
            ))
            log = CorreoLog(
                cliente_id = referidor.id,
                tipo       = TipoCorreo.reenvio,
                estado     = EstadoCorreo.enviado,
                asunto     = asunto,
            )
            db.add(log)
            db.commit()
    except Exception:
        pass   # correo es informativo, no interrumpe el rechazo

    return _serializar(solicitud, db)


# ─────────────────────────────────────────────────
# FUNCIÓN: Listar solicitudes
# ─────────────────────────────────────────────────
def listar_referidos(db: Session, pag: int = 1, estatus: str | None = None) -> dict:
    from app.models.referido_model_orm import SolicitudReferido, EstatusReferido

    query = db.query(SolicitudReferido)
    if estatus:
        try:
            e = EstatusReferido(estatus)
            query = query.filter(SolicitudReferido.estatus == e)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Estatus '{estatus}' no válido.")

    import math
    total  = query.count()
    ppag   = 20
    datos  = query.order_by(SolicitudReferido.fecha_solicitud.desc()) \
                  .offset((pag - 1) * ppag).limit(ppag).all()

    return {
        "total":           total,
        "pagina":          pag,
        "por_pagina":      ppag,
        "paginas_totales": math.ceil(total / ppag) if total > 0 else 1,
        "datos":           [_serializar(s, db) for s in datos],
    }


# ─────────────────────────────────────────────────
# HELPER: Serializar solicitud
# ─────────────────────────────────────────────────
def _serializar(s, db) -> dict:
    ref = s.referidor
    nombre_ref = " ".join(filter(None, [ref.nombres, ref.apellidos])) if ref else None
    return {
        "id":               s.id,
        "email_referido":   s.email_referido,
        "nombres_referido": s.nombres_referido,
        "referidor_id":     s.referidor_id,
        "referidor_email":  ref.email if ref else "—",
        "referidor_nombre": nombre_ref,
        "ruleta_id":        s.ruleta_id,
        "estatus":          s.estatus.value,
        "motivo_rechazo":   s.motivo_rechazo if s.estatus.value == "rechazado" else None,
        "fecha_solicitud":  str(s.fecha_solicitud),
        "fecha_resolucion": str(s.fecha_resolucion) if s.fecha_resolucion else None,
        "cliente_id":       s.cliente_id,
    }
