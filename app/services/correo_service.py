"""
=====================================================
SERVICIO DE CORREO - SISTEMA RULETA DE PREMIOS
=====================================================
Versión actualizada: incluye link de acceso a la
ruleta en el correo de invitación.
=====================================================
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models.models import (
    Cliente, CorreoLog, TipoCorreo, EstadoCorreo, EstatusCliente
)

# ─────────────────────────────────────────────────
# URL BASE del frontend (ajustar si cambia el host)
# ─────────────────────────────────────────────────
FRONTEND_URL = "http://127.0.0.1:8000/frontend"


# ─────────────────────────────────────────────────────────
# PLANTILLAS HTML
# ─────────────────────────────────────────────────────────

def _plantilla_invitacion(cliente: Cliente) -> tuple[str, str]:
    nombre = cliente.nombres or cliente.email.split("@")[0]
    link   = f"{FRONTEND_URL}?token={cliente.token}"
    asunto = "🎡 ¡Tu invitación a la Ruleta de Premios!"
    cuerpo = f"""
<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#0D0D14;font-family:'Segoe UI',Arial,sans-serif">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0D0D14;padding:40px 20px">
    <tr><td align="center">
      <table width="100%" style="max-width:560px;background:#12121A;border-radius:20px;overflow:hidden;border:1px solid rgba(212,175,55,0.2)">

        <!-- HEADER DORADO -->
        <tr>
          <td style="background:linear-gradient(135deg,#9A7B1A,#D4AF37);padding:32px;text-align:center">
            <div style="font-size:2.8rem;margin-bottom:8px">🎡</div>
            <h1 style="margin:0;color:#0D0D14;font-size:1.8rem;letter-spacing:3px;font-weight:900">
              RULETA DE PREMIOS
            </h1>
            <p style="margin:6px 0 0;color:rgba(10,10,15,0.7);font-size:.9rem">Evento Especial</p>
          </td>
        </tr>

        <!-- CUERPO -->
        <tr>
          <td style="padding:36px 32px">
            <p style="color:#F0EDE8;font-size:1.05rem;margin:0 0 8px">
              ¡Hola, <strong style="color:#D4AF37">{nombre}</strong>!
            </p>
            <p style="color:rgba(240,237,232,0.65);font-size:.92rem;line-height:1.7;margin:0 0 28px">
              Has sido invitado a participar en nuestra <strong style="color:#F0EDE8">Ruleta de Premios</strong>.
              Gira la ruleta y descubre qué premio increíble te espera.
            </p>

            <!-- CÓDIGO DE ACCESO -->
            <div style="background:#1C1C28;border:1px solid rgba(212,175,55,0.25);border-radius:14px;padding:20px 24px;margin-bottom:28px;text-align:center">
              <p style="color:rgba(240,237,232,0.5);font-size:.72rem;letter-spacing:2px;text-transform:uppercase;margin:0 0 10px">Tu código de acceso</p>
              <div style="font-family:'Courier New',monospace;font-size:1.4rem;font-weight:700;color:#F5D76E;letter-spacing:4px;background:#0D0D14;padding:12px 20px;border-radius:10px;display:inline-block">
                {cliente.token}
              </div>
              <p style="color:rgba(240,237,232,0.4);font-size:.75rem;margin:10px 0 0">Úsalo para acceder a la ruleta — válido por un solo giro</p>
            </div>

            <!-- BOTÓN PRINCIPAL -->
            <div style="text-align:center;margin-bottom:28px">
              <a href="{link}"
                 style="display:inline-block;background:linear-gradient(135deg,#9A7B1A,#D4AF37);color:#0D0D14;text-decoration:none;padding:16px 40px;border-radius:12px;font-weight:700;font-size:1.05rem;letter-spacing:1px;box-shadow:0 4px 20px rgba(212,175,55,0.4)">
                🎰 &nbsp; ¡IR A LA RULETA!
              </a>
            </div>

            <p style="color:rgba(240,237,232,0.4);font-size:.78rem;text-align:center;margin:0;line-height:1.6">
              Si el botón no funciona, copia y pega este enlace en tu navegador:<br>
              <a href="{link}" style="color:#D4AF37;word-break:break-all">{link}</a>
            </p>
          </td>
        </tr>

        <!-- FOOTER -->
        <tr>
          <td style="background:#0A0A0F;padding:20px 32px;border-top:1px solid rgba(255,255,255,0.06)">
            <p style="color:rgba(240,237,232,0.25);font-size:.75rem;text-align:center;margin:0;line-height:1.6">
              Este correo fue enviado porque fuiste registrado en el sistema de Ruleta de Premios.<br>
              © 2026 Ruleta de Premios — Todos los derechos reservados.
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>
"""
    return asunto, cuerpo


def _plantilla_felicitacion(
    cliente: Cliente,
    nombre_premio: str,
    fecha_entrega: str | None = None,
    hora_entrega:  str | None = None,
    lugar_entrega: str | None = None,
    notas_entrega: str | None = None,
) -> tuple[str, str]:
    nombre = cliente.nombres or cliente.email.split("@")[0]
    asunto = f"🏆 ¡Felicitaciones {nombre}! Ganaste: {nombre_premio} — Detalles de entrega"

    # Bloque de entrega — solo si se proporcionaron datos
    tiene_entrega = fecha_entrega or lugar_entrega
    bloque_entrega = ""
    if tiene_entrega:
        filas = ""
        if fecha_entrega:
            filas += f"""
            <tr>
              <td style="padding:10px 14px;border-bottom:1px solid rgba(255,255,255,0.06)">
                <span style="font-size:.7rem;letter-spacing:1px;text-transform:uppercase;color:rgba(212,175,55,.6)">📅 Fecha</span>
                <div style="color:#F0EDE8;font-weight:600;margin-top:3px">{fecha_entrega}</div>
              </td>
            </tr>"""
        if hora_entrega:
            filas += f"""
            <tr>
              <td style="padding:10px 14px;border-bottom:1px solid rgba(255,255,255,0.06)">
                <span style="font-size:.7rem;letter-spacing:1px;text-transform:uppercase;color:rgba(212,175,55,.6)">🕐 Hora</span>
                <div style="color:#F0EDE8;font-weight:600;margin-top:3px">{hora_entrega}</div>
              </td>
            </tr>"""
        if lugar_entrega:
            filas += f"""
            <tr>
              <td style="padding:10px 14px;border-bottom:1px solid rgba(255,255,255,0.06)">
                <span style="font-size:.7rem;letter-spacing:1px;text-transform:uppercase;color:rgba(212,175,55,.6)">📍 Lugar</span>
                <div style="color:#F0EDE8;font-weight:600;margin-top:3px">{lugar_entrega}</div>
              </td>
            </tr>"""
        if notas_entrega:
            filas += f"""
            <tr>
              <td style="padding:10px 14px">
                <span style="font-size:.7rem;letter-spacing:1px;text-transform:uppercase;color:rgba(212,175,55,.6)">📝 Indicaciones</span>
                <div style="color:rgba(240,237,232,.7);font-size:.85rem;margin-top:3px;line-height:1.5">{notas_entrega}</div>
              </td>
            </tr>"""

        bloque_entrega = f"""
            <div style="margin-bottom:24px">
              <p style="color:#F0EDE8;font-size:.8rem;font-weight:700;letter-spacing:1px;text-transform:uppercase;margin:0 0 10px">
                📦 Detalles de entrega
              </p>
              <table width="100%" style="background:#1C1C28;border:1px solid rgba(212,175,55,.2);border-radius:12px;border-collapse:collapse;overflow:hidden">
                {filas}
              </table>
            </div>"""
    else:
        bloque_entrega = """
            <p style="color:rgba(240,237,232,.55);font-size:.88rem;line-height:1.7;margin:0 0 20px">
              Nos pondremos en contacto contigo pronto para coordinar la entrega.
              Por favor mantén este correo como comprobante.
            </p>"""

    cuerpo = f"""
<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#0D0D14;font-family:'Segoe UI',Arial,sans-serif">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0D0D14;padding:40px 20px">
    <tr><td align="center">
      <table width="100%" style="max-width:560px;background:#12121A;border-radius:20px;overflow:hidden;border:1px solid rgba(212,175,55,0.2)">

        <tr>
          <td style="background:linear-gradient(135deg,#9A7B1A,#D4AF37);padding:32px;text-align:center">
            <div style="font-size:3rem;margin-bottom:8px">🏆</div>
            <h1 style="margin:0;color:#0D0D14;font-size:1.8rem;letter-spacing:2px;font-weight:900">¡FELICITACIONES!</h1>
          </td>
        </tr>

        <tr>
          <td style="padding:36px 32px">
            <p style="color:#F0EDE8;font-size:1.05rem;margin:0 0 16px">
              ¡Hola, <strong style="color:#D4AF37">{nombre}</strong>!
            </p>
            <p style="color:rgba(240,237,232,0.65);font-size:.92rem;line-height:1.7;margin:0 0 22px">
              Giraste la ruleta y ganaste un premio increíble. ¡Enhorabuena!
            </p>

            <div style="background:linear-gradient(135deg,rgba(212,175,55,.12),rgba(212,175,55,.05));border:1px solid rgba(212,175,55,.35);border-radius:14px;padding:22px;text-align:center;margin-bottom:24px">
              <p style="color:rgba(240,237,232,.5);font-size:.7rem;letter-spacing:2px;text-transform:uppercase;margin:0 0 8px">Tu premio</p>
              <p style="color:#F5D76E;font-size:1.7rem;font-weight:800;margin:0;letter-spacing:1px">{nombre_premio}</p>
            </div>

            {bloque_entrega}

            <div style="background:#1C1C28;border-radius:10px;padding:14px 16px;font-size:.82rem;color:rgba(240,237,232,.5);line-height:1.6">
              💡 Guarda este correo como <strong style="color:rgba(240,237,232,.7)">comprobante oficial</strong> de tu premio.
            </div>
          </td>
        </tr>

        <tr>
          <td style="background:#0A0A0F;padding:18px 32px;border-top:1px solid rgba(255,255,255,.06)">
            <p style="color:rgba(240,237,232,.22);font-size:.73rem;text-align:center;margin:0">
              © 2026 Ruleta de Premios — Todos los derechos reservados.
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""
    return asunto, cuerpo


def _plantilla_referido(cliente: Cliente, referidor_nombre: str) -> tuple[str, str]:
    nombre = cliente.nombres or cliente.email.split("@")[0]
    link   = f"{FRONTEND_URL}?token={cliente.token}"
    asunto = f"🎡 {referidor_nombre} te invita a la Ruleta de Premios"
    cuerpo = f"""
<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#0D0D14;font-family:'Segoe UI',Arial,sans-serif">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0D0D14;padding:40px 20px">
    <tr><td align="center">
      <table width="100%" style="max-width:560px;background:#12121A;border-radius:20px;overflow:hidden;border:1px solid rgba(212,175,55,0.2)">
        <tr>
          <td style="background:linear-gradient(135deg,#9A7B1A,#D4AF37);padding:28px;text-align:center">
            <div style="font-size:2.5rem">🎁</div>
            <h1 style="margin:8px 0 0;color:#0D0D14;font-size:1.5rem;font-weight:900">FUISTE INVITADO</h1>
          </td>
        </tr>
        <tr>
          <td style="padding:32px">
            <p style="color:#F0EDE8;font-size:1rem;margin:0 0 12px">¡Hola, <strong style="color:#D4AF37">{nombre}</strong>!</p>
            <p style="color:rgba(240,237,232,0.65);font-size:.9rem;line-height:1.7;margin:0 0 24px">
              <strong style="color:#F0EDE8">{referidor_nombre}</strong> te ha referido para participar en la Ruleta de Premios.
            </p>
            <div style="background:#1C1C28;border-radius:12px;padding:18px;text-align:center;margin-bottom:24px">
              <p style="color:rgba(240,237,232,0.5);font-size:.7rem;letter-spacing:2px;text-transform:uppercase;margin:0 0 8px">Tu código</p>
              <div style="font-family:'Courier New',monospace;font-size:1.3rem;font-weight:700;color:#F5D76E;letter-spacing:4px">{cliente.token}</div>
            </div>
            <div style="text-align:center">
              <a href="{link}" style="display:inline-block;background:linear-gradient(135deg,#9A7B1A,#D4AF37);color:#0D0D14;text-decoration:none;padding:14px 36px;border-radius:12px;font-weight:700;font-size:1rem">
                🎰 ¡IR A LA RULETA!
              </a>
            </div>
          </td>
        </tr>
        <tr>
          <td style="background:#0A0A0F;padding:16px 32px;border-top:1px solid rgba(255,255,255,0.06)">
            <p style="color:rgba(240,237,232,0.25);font-size:.75rem;text-align:center;margin:0">© 2026 Ruleta de Premios</p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>
"""
    return asunto, cuerpo


# ─────────────────────────────────────────────────
# REGISTRAR LOG
# ─────────────────────────────────────────────────
def _registrar_log(db, cliente_id, tipo, estado, asunto, lote_id=None, error_msg=None):
    log = CorreoLog(
        cliente_id  = cliente_id,
        tipo        = tipo,
        estado      = estado,
        asunto      = asunto,
        lote_id     = lote_id,
        error_msg   = error_msg,
        fecha_envio = datetime.utcnow(),
    )
    db.add(log)
    db.flush()
    return log


# ─────────────────────────────────────────────────
# ENVIAR CORREO INDIVIDUAL
# ─────────────────────────────────────────────────
async def enviar_correo_individual(
    db, cliente, tipo, nombre_premio=None, referidor=None
) -> dict:
    if tipo == TipoCorreo.invitacion:
        asunto, cuerpo = _plantilla_invitacion(cliente)
    elif tipo == TipoCorreo.felicitacion:
        asunto, cuerpo = _plantilla_felicitacion(cliente, nombre_premio or "Premio")
    elif tipo == TipoCorreo.referido:
        asunto, cuerpo = _plantilla_referido(cliente, referidor or "Un amigo")
    else:
        asunto, cuerpo = _plantilla_invitacion(cliente)

    enviado = False
    error   = None

    try:
        from fastapi_mail import FastMail, MessageSchema, ConnectionConfig

        # ── Configurar credenciales ──────────────────
        # Temporalmente hardcodeado — mover a settings cuando el .env esté confirmado
        from app.config import settings
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


# ─────────────────────────────────────────────────
# ENVÍO MASIVO EN LOTES (Req. #5)
# ─────────────────────────────────────────────────
async def enviar_masivo_invitacion(db, clientes, lote_size=500) -> dict:
    total = len(clientes)
    enviados = fallidos = 0
    lotes = []

    for i in range(0, total, lote_size):
        lote    = clientes[i:i + lote_size]
        lote_id = str(uuid.uuid4())[:8]
        lote_ok = lote_err = 0

        for cliente in lote:
            resultado = await enviar_correo_individual(db, cliente, TipoCorreo.invitacion)
            ultimo_log = db.query(CorreoLog).filter(
                CorreoLog.cliente_id == cliente.id
            ).order_by(CorreoLog.id.desc()).first()
            if ultimo_log:
                ultimo_log.lote_id = lote_id
                db.flush()

            if resultado["estado"] == EstadoCorreo.enviado.value:
                lote_ok  += 1; enviados += 1
            else:
                lote_err += 1; fallidos += 1

        db.commit()
        lotes.append({"lote_id": lote_id, "enviados": lote_ok, "fallidos": lote_err})

    return {
        "total": total, "enviados": enviados,
        "fallidos": fallidos, "lotes_procesados": len(lotes),
        "detalle_lotes": lotes,
    }


# ─────────────────────────────────────────────────
# REENVÍO INDIVIDUAL (Req. #10)
# ─────────────────────────────────────────────────
async def reenviar_correo(db, cliente_id: int) -> dict:
    from app.models.models import Cliente
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        return {"error": f"Cliente {cliente_id} no encontrado."}
    return await enviar_correo_individual(db, cliente, TipoCorreo.reenvio)
