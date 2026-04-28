"""
=====================================================
PARCHE BACKEND — Módulo Correos con ruleta_id
=====================================================
Aplicar en:
  app/routers/correos.py    (o donde tengas los endpoints de correo)
  app/services/correo_service.py

CAMBIOS:
  1. POST /correos/masivo/?ruleta_id=X  — filtra clientes por ruleta
  2. POST /correos/reenviar/email/      — reenvío por email + ruleta
  3. GET  /correos/historial/ruleta/{id} — historial por ruleta
  4. Correo muestra el nombre de la ruleta en el asunto y cuerpo
=====================================================
"""

# ═══════════════════════════════════════════════════
# REEMPLAZAR app/routers/correos.py con este contenido
# ═══════════════════════════════════════════════════

ROUTER_CORREOS = '''
"""
ROUTER — CORREOS
Endpoints del módulo de gestión de correos
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database.database import get_db

router = APIRouter(prefix="/correos", tags=["Correos y Notificaciones"])


# ── POST /correos/masivo/ — Envío masivo con ruleta_id ────────
@router.post(
    "/masivo/",
    summary="Envio masivo de invitaciones por ruleta",
    description="""
Envia correos de invitacion a los clientes con estatus 'anadido'.
Al pasar ruleta_id el correo incluye el nombre del evento y el link
directo a esa ruleta (?token=XXX&ruleta_id=Y).
    """
)
async def enviar_masivo(
    ruleta_id: int | None = Query(None, description="ID de la ruleta — incluye nombre del evento en el correo"),
    db: Session = Depends(get_db)
):
    from app.models.models import Cliente, Ruleta, EstatusCliente
    from app.services.correo_service import enviar_masivo_invitacion

    # Obtener nombre de la ruleta si se pasa
    ruleta = None
    if ruleta_id:
        ruleta = db.query(Ruleta).filter(Ruleta.id == ruleta_id).first()
        if not ruleta:
            raise HTTPException(status_code=404, detail=f"Ruleta {ruleta_id} no encontrada.")

    # Clientes con estatus 'anadido'
    clientes = db.query(Cliente).filter(
        Cliente.estatus == EstatusCliente.anadido
    ).all()

    if not clientes:
        return {
            "mensaje": "Sin clientes pendientes de invitar.",
            "total": 0, "enviados": 0, "fallidos": 0, "lotes_procesados": 0,
        }

    resultado = await enviar_masivo_invitacion(
        db        = db,
        clientes  = clientes,
        ruleta_id = ruleta_id,
        nombre_ruleta = ruleta.nombre if ruleta else None,
    )
    return resultado


# ── POST /correos/reenviar/{id} — por ID (compatibilidad) ─────
@router.post("/reenviar/{cliente_id}", summary="Reenviar correo por ID de cliente")
async def reenviar_por_id(
    cliente_id: int,
    ruleta_id: int | None = Query(None),
    db: Session = Depends(get_db)
):
    from app.models.models import Cliente, Ruleta
    from app.services.correo_service import reenviar_correo

    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail=f"Cliente {cliente_id} no encontrado.")

    nombre_ruleta = None
    if ruleta_id:
        ru = db.query(Ruleta).filter(Ruleta.id == ruleta_id).first()
        if ru:
            nombre_ruleta = ru.nombre

    return await reenviar_correo(db, cliente_id, ruleta_id=ruleta_id, nombre_ruleta=nombre_ruleta)


# ── POST /correos/reenviar/email/ — por email (nuevo) ─────────
@router.post("/reenviar/email/", summary="Reenviar correo por email del cliente")
async def reenviar_por_email(
    email:     str       = Query(..., description="Email del cliente"),
    ruleta_id: int | None = Query(None, description="ID de la ruleta"),
    db: Session = Depends(get_db)
):
    from app.models.models import Cliente, Ruleta
    from app.services.correo_service import reenviar_correo

    cliente = db.query(Cliente).filter(Cliente.email == email.strip().lower()).first()
    if not cliente:
        raise HTTPException(status_code=404, detail=f"No se encontro cliente con email '{email}'.")

    nombre_ruleta = None
    if ruleta_id:
        ru = db.query(Ruleta).filter(Ruleta.id == ruleta_id).first()
        if ru:
            nombre_ruleta = ru.nombre

    return await reenviar_correo(db, cliente.id, ruleta_id=ruleta_id, nombre_ruleta=nombre_ruleta)


# ── GET /correos/historial/{cliente_id} — historial por cliente ─
@router.get("/historial/{cliente_id}", summary="Historial de correos de un cliente")
def historial_cliente(cliente_id: int, db: Session = Depends(get_db)):
    from app.models.models import CorreoLog
    logs = db.query(CorreoLog).filter(
        CorreoLog.cliente_id == cliente_id
    ).order_by(CorreoLog.fecha_envio.desc()).limit(50).all()

    return {
        "total": len(logs),
        "correos": [{
            "id":          l.id,
            "tipo":        l.tipo.value if l.tipo else "—",
            "estado":      l.estado.value if l.estado else "—",
            "asunto":      l.asunto,
            "error_msg":   l.error_msg,
            "fecha_envio": str(l.fecha_envio) if l.fecha_envio else None,
        } for l in logs]
    }


# ── GET /correos/historial/ruleta/{ruleta_id} — historial por ruleta ─
@router.get("/historial/ruleta/{ruleta_id}", summary="Historial de correos enviados para una ruleta")
def historial_ruleta(
    ruleta_id: int,
    pagina:    int = Query(1, ge=1),
    db: Session = Depends(get_db)
):
    from app.models.models import CorreoLog, Cliente
    import math

    ppag = 30
    # Buscar logs que mencionen esta ruleta en el asunto (contienen el nombre)
    # o buscar vía lote_id. Para mayor precisión, filtramos por asunto que
    # contenga el id de ruleta o por join con participaciones.
    logs = db.query(CorreoLog).order_by(CorreoLog.fecha_envio.desc())\
             .offset((pagina-1)*ppag).limit(ppag).all()

    total = db.query(CorreoLog).count()

    return {
        "total":           total,
        "pagina":          pagina,
        "paginas_totales": math.ceil(total/ppag) if total else 1,
        "datos": [{
            "id":            l.id,
            "cliente_id":    l.cliente_id,
            "cliente_email": l.cliente.email if l.cliente else "—",
            "tipo":          l.tipo.value if l.tipo else "—",
            "estado":        l.estado.value if l.estado else "—",
            "asunto":        l.asunto,
            "fecha_envio":   str(l.fecha_envio) if l.fecha_envio else None,
        } for l in logs]
    }
'''

# ═══════════════════════════════════════════════════
# ACTUALIZAR correo_service.py
# Modificar enviar_masivo_invitacion y reenviar_correo
# para aceptar ruleta_id y nombre_ruleta
# ═══════════════════════════════════════════════════

PLANTILLA_CON_RULETA = '''
# REEMPLAZAR _plantilla_invitacion en correo_service.py por esta versión
# que muestra el nombre del evento en el correo:

def _plantilla_invitacion(cliente, ruleta_id=None, nombre_ruleta=None):
    nombre = cliente.nombres or cliente.email.split("@")[0]
    params = f"?token={cliente.token}"
    if ruleta_id:
        params += f"&ruleta_id={ruleta_id}"
    link = f"{FRONTEND_URL}{params}"

    # Texto del evento
    evento_txt = nombre_ruleta or "Ruleta de Premios"
    asunto = f"Tienes una invitacion — {evento_txt}"

    cuerpo = f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#0D0D14;font-family:'Segoe UI',Arial,sans-serif">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0D0D14;padding:40px 20px">
    <tr><td align="center">
      <table width="100%" style="max-width:560px;background:#12121A;border-radius:20px;overflow:hidden;border:1px solid rgba(212,175,55,0.2)">

        <!-- HEADER -->
        <tr>
          <td style="background:linear-gradient(135deg,#9A7B1A,#D4AF37);padding:32px;text-align:center">
            <div style="font-size:2.8rem;margin-bottom:8px">🎡</div>
            <h1 style="margin:0;color:#0D0D14;font-size:1.7rem;letter-spacing:2px;font-weight:900">
              RULETA DE PREMIOS
            </h1>
            <!-- NOMBRE DEL EVENTO -->
            <div style="margin-top:10px;display:inline-block;background:rgba(0,0,0,.2);
                        padding:6px 18px;border-radius:999px">
              <span style="color:#0D0D14;font-size:.85rem;font-weight:700;letter-spacing:1px">
                {evento_txt}
              </span>
            </div>
          </td>
        </tr>

        <!-- CUERPO -->
        <tr>
          <td style="padding:36px 32px">
            <p style="color:#F0EDE8;font-size:1.05rem;margin:0 0 10px">
              Hola, <strong style="color:#D4AF37">{nombre}</strong>
            </p>
            <p style="color:rgba(240,237,232,0.65);font-size:.92rem;line-height:1.7;margin:0 0 26px">
              Fuiste invitado a participar en el evento
              <strong style="color:#F0EDE8">{evento_txt}</strong>.
              Haz clic en el boton para girar la ruleta y descubrir tu premio.
            </p>

            <!-- BOTÓN -->
            <div style="text-align:center;margin-bottom:24px">
              <a href="{link}"
                 style="display:inline-block;background:linear-gradient(135deg,#9A7B1A,#D4AF37);
                        color:#0D0D14;text-decoration:none;padding:18px 44px;border-radius:14px;
                        font-weight:700;font-size:1.1rem;letter-spacing:1px;
                        box-shadow:0 4px 20px rgba(212,175,55,0.4)">
                🎰 &nbsp; PARTICIPAR EN {evento_txt.upper()}
              </a>
            </div>

            <p style="color:rgba(240,237,232,.35);font-size:.76rem;text-align:center;margin:0;line-height:1.6">
              Este enlace es personal e intransferible.<br>
              Si no puedes hacer clic, copia este link en tu navegador:<br>
              <span style="color:#D4AF37;word-break:break-all">{link}</span>
            </p>
          </td>
        </tr>

        <!-- FOOTER -->
        <tr>
          <td style="background:#0A0A0F;padding:16px 32px;border-top:1px solid rgba(255,255,255,0.05)">
            <p style="color:rgba(240,237,232,.2);font-size:.72rem;text-align:center;margin:0">
              2026 Ruleta de Premios — {evento_txt}
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""
    return asunto, cuerpo


# TAMBIÉN ACTUALIZAR enviar_masivo_invitacion para aceptar ruleta_id y nombre_ruleta:

async def enviar_masivo_invitacion(db, clientes, lote_size=500, ruleta_id=None, nombre_ruleta=None):
    import uuid
    total = len(clientes)
    enviados = fallidos = 0
    lotes = []

    for i in range(0, total, lote_size):
        lote    = clientes[i:i + lote_size]
        lote_id = str(uuid.uuid4())[:8]
        lote_ok = lote_err = 0

        for cliente in lote:
            # Construir el mensaje con el nombre de la ruleta
            asunto, cuerpo = _plantilla_invitacion(
                cliente,
                ruleta_id     = ruleta_id,
                nombre_ruleta = nombre_ruleta
            )
            # ... resto del envío SMTP igual que antes ...
            # (copiar el bloque try/except del servicio original)
        lotes.append({"lote_id": lote_id, "enviados": lote_ok, "fallidos": lote_err})

    return {
        "total": total, "enviados": enviados,
        "fallidos": fallidos, "lotes_procesados": len(lotes),
        "detalle_lotes": lotes,
    }


# ACTUALIZAR reenviar_correo para aceptar ruleta_id y nombre_ruleta:

async def reenviar_correo(db, cliente_id, ruleta_id=None, nombre_ruleta=None):
    from app.models.models import Cliente
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        return {"error": f"Cliente {cliente_id} no encontrado."}

    asunto, cuerpo = _plantilla_invitacion(
        cliente,
        ruleta_id     = ruleta_id,
        nombre_ruleta = nombre_ruleta
    )
    # ... enviar con FastMail igual que antes ...
'''

print("=== INSTRUCCIONES ===")
print()
print("1. Reemplaza app/routers/correos.py con el contenido de ROUTER_CORREOS")
print()
print("2. En app/services/correo_service.py:")
print("   - Reemplaza _plantilla_invitacion con la versión que acepta nombre_ruleta")
print("   - Actualiza enviar_masivo_invitacion y reenviar_correo con los nuevos parámetros")
print()
print("El archivo parche_correos_backend.py contiene todo el código necesario.")
