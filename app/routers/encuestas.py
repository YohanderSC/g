"""
=====================================================
ROUTER - ENCUESTAS
=====================================================
Endpoints admin:
  POST   /encuestas/                → Crear pregunta
  GET    /encuestas/                → Listar preguntas
  PATCH  /encuestas/{id}            → Editar pregunta
  DELETE /encuestas/{id}            → Eliminar pregunta
  GET    /encuestas/respuestas/     → Ver respuestas (con filtros)

Endpoints cliente (sin auth):
  GET    /encuestas/ruleta/{id}     → Obtener preguntas de una ruleta
  POST   /encuestas/responder/      → Guardar respuestas del cliente
=====================================================
"""
import json
import math
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.encuesta_model import PreguntaEncuesta, RespuestaEncuesta, TipoPregunta
from app.models.models import Cliente

router = APIRouter(prefix="/encuestas", tags=["Encuestas"])

POR_PAGINA = 20


# ── Schemas ───────────────────────────────────────
class PreguntaCreate(BaseModel):
    texto:       str
    tipo:        TipoPregunta   = TipoPregunta.texto_libre
    opciones:    Optional[list[str]] = None   # Solo para opcion_multiple
    obligatoria: bool           = False
    activa:      bool           = True
    orden:       int            = 0
    ruleta_id:   Optional[int]  = None   # None = aplica a todas las ruletas

class PreguntaUpdate(BaseModel):
    texto:       Optional[str]          = None
    tipo:        Optional[TipoPregunta] = None
    opciones:    Optional[list[str]]    = None
    obligatoria: Optional[bool]         = None
    activa:      Optional[bool]         = None
    orden:       Optional[int]          = None
    ruleta_id:   Optional[int]          = None

class RespuestaItem(BaseModel):
    pregunta_id: int
    respuesta:   str

class ResponderRequest(BaseModel):
    token:      str
    ruleta_id:  Optional[int] = None
    respuestas: list[RespuestaItem]


# ── ADMIN: Crear pregunta ─────────────────────────
@router.post("/", status_code=201, summary="Crear pregunta de encuesta")
def crear_pregunta(datos: PreguntaCreate, db: Session = Depends(get_db)):
    opciones_json = json.dumps(datos.opciones, ensure_ascii=False) if datos.opciones else None
    p = PreguntaEncuesta(
        texto       = datos.texto,
        tipo        = datos.tipo,
        opciones    = opciones_json,
        obligatoria = datos.obligatoria,
        activa      = datos.activa,
        orden       = datos.orden,
        ruleta_id   = datos.ruleta_id,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return _serializar(p)


# ── ADMIN: Listar preguntas ───────────────────────
@router.get("/", summary="Listar preguntas de encuesta")
def listar_preguntas(
    pagina:    int      = Query(1, ge=1),
    ruleta_id: int | None = Query(None),
    solo_activas: bool  = Query(False),
    db: Session = Depends(get_db)
):
    q = db.query(PreguntaEncuesta)
    if ruleta_id is not None:
        q = q.filter(
            (PreguntaEncuesta.ruleta_id == ruleta_id) |
            (PreguntaEncuesta.ruleta_id == None)
        )
    if solo_activas:
        q = q.filter(PreguntaEncuesta.activa == True)

    total = q.count()
    datos = q.order_by(PreguntaEncuesta.orden, PreguntaEncuesta.id)\
             .offset((pagina-1)*POR_PAGINA).limit(POR_PAGINA).all()

    return {
        "total": total, "pagina": pagina,
        "por_pagina": POR_PAGINA,
        "paginas_totales": math.ceil(total/POR_PAGINA) if total > 0 else 1,
        "datos": [_serializar(p) for p in datos]
    }


# ── ADMIN: Editar pregunta ────────────────────────
@router.patch("/{pregunta_id}", summary="Editar pregunta de encuesta")
def editar_pregunta(pregunta_id: int, datos: PreguntaUpdate, db: Session = Depends(get_db)):
    p = db.query(PreguntaEncuesta).filter(PreguntaEncuesta.id == pregunta_id).first()
    if not p:
        raise HTTPException(status_code=404, detail=f"Pregunta {pregunta_id} no encontrada.")

    campos = datos.model_dump(exclude_unset=True)
    if "opciones" in campos:
        p.opciones = json.dumps(campos.pop("opciones"), ensure_ascii=False) if campos.get("opciones") else None
    for k, v in campos.items():
        setattr(p, k, v)

    db.commit()
    db.refresh(p)
    return _serializar(p)


# ── ADMIN: Eliminar pregunta ──────────────────────
@router.delete("/{pregunta_id}", summary="Eliminar pregunta de encuesta")
def eliminar_pregunta(pregunta_id: int, db: Session = Depends(get_db)):
    p = db.query(PreguntaEncuesta).filter(PreguntaEncuesta.id == pregunta_id).first()
    if not p:
        raise HTTPException(status_code=404, detail=f"Pregunta {pregunta_id} no encontrada.")
    db.delete(p)
    db.commit()
    return {"mensaje": f"Pregunta {pregunta_id} eliminada."}


# ── ADMIN: Ver respuestas ─────────────────────────
@router.get("/respuestas/", summary="Ver respuestas de encuesta")
def ver_respuestas(
    pagina:      int       = Query(1, ge=1),
    pregunta_id: int | None = Query(None),
    ruleta_id:   int | None = Query(None),
    db: Session = Depends(get_db)
):
    q = db.query(RespuestaEncuesta)
    if pregunta_id:
        q = q.filter(RespuestaEncuesta.pregunta_id == pregunta_id)
    if ruleta_id:
        q = q.filter(RespuestaEncuesta.ruleta_id == ruleta_id)

    total = q.count()
    datos = q.order_by(RespuestaEncuesta.fecha.desc())\
             .offset((pagina-1)*POR_PAGINA).limit(POR_PAGINA).all()

    return {
        "total": total, "pagina": pagina,
        "por_pagina": POR_PAGINA,
        "paginas_totales": math.ceil(total/POR_PAGINA) if total > 0 else 1,
        "datos": [{
            "id":           r.id,
            "pregunta":     r.pregunta.texto if r.pregunta else "—",
            "tipo":         r.pregunta.tipo.value if r.pregunta else "—",
            "respuesta":    r.respuesta,
            "cliente_email": r.cliente.email if r.cliente else "—",
            "cliente_nombre": f"{r.cliente.nombres or ''} {r.cliente.apellidos or ''}".strip() if r.cliente else "—",
            "fecha":        str(r.fecha),
        } for r in datos]
    }


# ── CLIENTE: Obtener preguntas activas de una ruleta ─
@router.get("/ruleta/{ruleta_id}", summary="Obtener preguntas activas para una ruleta (cliente)")
def preguntas_para_ruleta(ruleta_id: int, db: Session = Depends(get_db)):
    """
    Devuelve las preguntas activas para una ruleta específica
    (globales + las específicas de esa ruleta).
    """
    preguntas = db.query(PreguntaEncuesta).filter(
        PreguntaEncuesta.activa == True,
        (PreguntaEncuesta.ruleta_id == ruleta_id) |
        (PreguntaEncuesta.ruleta_id == None)
    ).order_by(PreguntaEncuesta.orden, PreguntaEncuesta.id).all()

    return { "total": len(preguntas), "preguntas": [_serializar(p) for p in preguntas] }


# ── CLIENTE: Guardar respuestas ───────────────────
@router.post("/responder/", summary="Guardar respuestas del cliente")
def guardar_respuestas(datos: ResponderRequest, db: Session = Depends(get_db)):
    """
    Guarda las respuestas de un cliente. Se identifica por su token.
    No bloquea si ya respondió antes (puede responder varias ruletas).
    """
    cliente = db.query(Cliente).filter(Cliente.token == datos.token).first()
    if not cliente:
        raise HTTPException(status_code=401, detail="Token inválido.")

    guardadas = 0
    for r in datos.respuestas:
        if not r.respuesta.strip():
            continue
        resp = RespuestaEncuesta(
            pregunta_id = r.pregunta_id,
            cliente_id  = cliente.id,
            ruleta_id   = datos.ruleta_id,
            respuesta   = r.respuesta.strip(),
        )
        db.add(resp)
        guardadas += 1

    db.commit()
    return {"guardadas": guardadas, "mensaje": "Respuestas guardadas correctamente ✅"}


# ── HELPER ────────────────────────────────────────
def _serializar(p: PreguntaEncuesta) -> dict:
    opciones = None
    if p.opciones:
        try:
            opciones = json.loads(p.opciones)
        except Exception:
            opciones = []
    return {
        "id":          p.id,
        "texto":       p.texto,
        "tipo":        p.tipo.value,
        "opciones":    opciones,
        "obligatoria": p.obligatoria,
        "activa":      p.activa,
        "orden":       p.orden,
        "ruleta_id":   p.ruleta_id,
    }
