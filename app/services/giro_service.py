"""
=====================================================
SERVICIO DE GIRO - SISTEMA RULETA DE PREMIOS
=====================================================
Descripción: Lógica central del giro de la ruleta.

Flujo completo:
  1. Validar token del cliente
  2. Verificar que la ruleta está activa
  3. Verificar que el cliente no ha girado ya
  4. Verificar si el cliente tiene premio condicionado
  5. Si no, asignar premio aleatorio ponderado
  6. Registrar participación
  7. Actualizar estatus del cliente
  8. Descontar inventario del premio
  9. Registrar correo de felicitación (pendiente)

Requerimientos cubiertos:
  #4  - Validación de token único
  #6  - Asignación aleatoria ponderada por porcentaje_prob
  #7  - Verificación de premios condicionados primero
  #8  - Envío de correo de felicitación al ganador
  #11 - Datos para reporte de participación
=====================================================
"""
import random
from datetime import datetime
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.models import (
    Cliente, Ruleta, Premio, Participacion, PremioCondicionado,
    CorreoLog, EstatusCliente, EstadoCorreo, TipoCorreo
)


# ─────────────────────────────────────────────────────────
# FUNCIÓN PRINCIPAL: Ejecutar giro
# ─────────────────────────────────────────────────────────
def ejecutar_giro(db: Session, token: str, ruleta_id: int) -> dict:
    """
    Ejecuta el giro completo de la ruleta para un cliente.
    Retorna el resultado con el premio asignado.
    """

    # ── PASO 1: Validar token ─────────────────────────
    # El token identifica al cliente — no se bloquea globalmente.
    # La restricción de "un giro por ruleta" se valida en el PASO 3.
    cliente = db.query(Cliente).filter(
        Cliente.token == token,
    ).first()

    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido. Verifica tu código de acceso."
        )

    # ── PASO 2: Validar ruleta activa ─────────────────
    ruleta = db.query(Ruleta).filter(
        Ruleta.id == ruleta_id,
        Ruleta.activa == True
    ).first()

    if not ruleta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"La ruleta {ruleta_id} no existe o no está activa."
        )

    # Verificar que la ruleta está dentro del rango de fechas
    ahora = datetime.utcnow()
    if ahora < ruleta.fecha_inicio.replace(tzinfo=None):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"La ruleta '{ruleta.nombre}' aún no ha iniciado."
        )
    if ruleta.fecha_cierre and ahora > ruleta.fecha_cierre.replace(tzinfo=None):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"La ruleta '{ruleta.nombre}' ya cerró."
        )

    # ── PASO 3: Verificar que no ha participado ya ────
    participacion_previa = db.query(Participacion).filter(
        Participacion.cliente_id == cliente.id,
        Participacion.ruleta_id  == ruleta_id
    ).first()

    if participacion_previa:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este cliente ya participó en esta ruleta. Solo se permite un giro por cliente."
        )

    # ── PASO 4: Verificar premio condicionado (Req. #7) ──
    premio = _verificar_premio_condicionado(db, cliente, ruleta_id)
    es_condicionado = premio is not None

    # ── PASO 5: Si no tiene condicionado → asignación aleatoria (Req. #6) ──
    if not premio:
        premio = _asignar_premio_aleatorio(db, ruleta_id)

    # ── PASO 6: Registrar participación ───────────────
    participacion = Participacion(
        cliente_id          = cliente.id,
        ruleta_id           = ruleta_id,
        premio_id           = premio.id if premio else None,
        fecha_participacion = datetime.utcnow(),
        premio_entregado    = False,
        token_usado         = token,
    )
    db.add(participacion)

    # ── PASO 7: Actualizar cliente ────────────────────
    # token_usado ya NO se marca globalmente — el cliente puede
    # participar en otras ruletas con el mismo token.
    # Solo se actualiza el estatus y el premio si aplica.
    cliente.estatus = EstatusCliente.participo
    if premio:
        cliente.premio_id = premio.id

    # ── PASO 8: Descontar inventario ──────────────────
    if premio:
        if premio.cantidad_disponible <= 0:
            # Si no hay disponibles, asignar sin descontar (log de advertencia)
            pass
        else:
            premio.cantidad_disponible -= 1

    # ── PASO 9: Registrar correo de felicitación ──────
    if premio:
        log_correo = CorreoLog(
            cliente_id  = cliente.id,
            tipo        = TipoCorreo.felicitacion,
            estado      = EstadoCorreo.pendiente,
            asunto      = f"Felicitaciones - Ganaste: {premio.nombre}",
            fecha_envio = datetime.utcnow(),
        )
        db.add(log_correo)

    db.commit()
    db.refresh(participacion)

    return {
        "participacion_id": participacion.id,
        "cliente_id":       cliente.id,
        "cliente_email":    cliente.email,
        "ruleta_id":        ruleta.id,
        "ruleta_nombre":    ruleta.nombre,
        "premio_id":        premio.id    if premio else None,
        "premio_nombre":    premio.nombre if premio else "Sin premio",
        "premio_imagen":    premio.imagen_url if premio else None,
        "es_condicionado":  es_condicionado,
        "fecha":            participacion.fecha_participacion,
        "mensaje":          f"¡Felicitaciones! Ganaste: {premio.nombre}" if premio
                            else "Gracias por participar. ¡Mejor suerte la próxima vez!",
    }


# ─────────────────────────────────────────────────────────
# FUNCIÓN: Verificar premio condicionado (Req. #7)
# Revisa si el cliente tiene un premio reservado antes
# de ejecutar el sorteo aleatorio.
# ─────────────────────────────────────────────────────────
def _verificar_premio_condicionado(
    db: Session, cliente: Cliente, ruleta_id: int
) -> Optional[Premio]:
    """
    Busca si hay un premio reservado para el email del cliente.
    Si encuentra uno, lo marca como entregado y lo retorna.
    """
    condicionado = db.query(PremioCondicionado).join(Premio).filter(
        PremioCondicionado.email_cliente == cliente.email,
        PremioCondicionado.entregado     == False,
        Premio.ruleta_id                 == ruleta_id,
    ).first()

    if condicionado:
        condicionado.entregado = True
        db.flush()
        return condicionado.premio

    return None


# ─────────────────────────────────────────────────────────
# FUNCIÓN: Asignación aleatoria ponderada (Req. #6)
# Selecciona un premio basado en su porcentaje_prob.
# ─────────────────────────────────────────────────────────
def _asignar_premio_aleatorio(
    db: Session, ruleta_id: int
) -> Optional[Premio]:
    """
    Selecciona un premio de forma aleatoria ponderada.

    Algoritmo:
      1. Obtiene premios disponibles con probabilidad > 0
      2. Construye una ruleta de probabilidades normalizadas
      3. Usa random.choices() con pesos para la selección
      4. Si la suma de probabilidades < 100%, el resto es "sin premio"
    """
    premios = db.query(Premio).filter(
        Premio.ruleta_id            == ruleta_id,
        Premio.cantidad_disponible  >  0,
        Premio.porcentaje_prob      >  0,
        Premio.es_condicionado      == False,
    ).all()

    if not premios:
        return None

    # Construir lista de pesos para random.choices
    pesos  = [float(p.porcentaje_prob) for p in premios]
    total  = sum(pesos)

    # El porcentaje restante representa "sin premio"
    sin_premio_peso = max(0.0, 100.0 - total)

    # Agregar opción "sin premio" a la lista
    opciones = premios + [None]
    pesos.append(sin_premio_peso if sin_premio_peso > 0 else 0.001)

    # Selección aleatoria ponderada
    resultado = random.choices(opciones, weights=pesos, k=1)[0]
    return resultado


# ─────────────────────────────────────────────────────────
# FUNCIÓN: Obtener estadísticas de participación (Req. #11)
# ─────────────────────────────────────────────────────────
def obtener_estadisticas(db: Session, ruleta_id: int) -> dict:
    """
    Genera el reporte de participación para una ruleta.
    Incluye estadísticas globales y por agencia.
    """
    ruleta = db.query(Ruleta).filter(Ruleta.id == ruleta_id).first()
    if not ruleta:
        raise HTTPException(status_code=404, detail=f"Ruleta {ruleta_id} no encontrada.")

    from app.models.models import Agencia

    # Totales generales
    total_clientes       = db.query(Cliente).count()
    total_participaciones = db.query(Participacion).filter(
        Participacion.ruleta_id == ruleta_id
    ).count()
    porc_global = round((total_participaciones / total_clientes * 100), 2) if total_clientes > 0 else 0

    # Premios
    premios_entregados  = db.query(Premio).filter(Premio.ruleta_id == ruleta_id).with_entities(
        db.query(Premio.cantidad_entregada).filter(Premio.ruleta_id == ruleta_id).scalar() or 0
    ).scalar() or 0
    premios_disponibles = db.query(Premio).filter(Premio.ruleta_id == ruleta_id).with_entities(
        db.query(Premio.cantidad_disponible).filter(Premio.ruleta_id == ruleta_id).scalar() or 0
    ).scalar() or 0

    # Por agencia
    agencias = db.query(Agencia).filter(Agencia.activa == True).all()
    stats_agencias = []
    for ag in agencias:
        clientes_ag = db.query(Cliente).filter(Cliente.agencia_id == ag.id).count()
        participaron = db.query(Participacion).join(Cliente).filter(
            Cliente.agencia_id   == ag.id,
            Participacion.ruleta_id == ruleta_id
        ).count()
        porc = round((participaron / clientes_ag * 100), 2) if clientes_ag > 0 else 0
        stats_agencias.append({
            "agencia_id":     ag.id,
            "agencia_nombre": ag.nombre,
            "total_clientes": clientes_ag,
            "participaron":   participaron,
            "porcentaje":     porc,
        })

    # Ganadores
    ganadores = db.query(Participacion).join(Premio).join(Cliente).filter(
        Participacion.ruleta_id != None,
        Participacion.premio_id != None,
        Participacion.ruleta_id == ruleta_id,
    ).all()

    lista_ganadores = [{
        "cliente_email": g.cliente.email,
        "cliente_nombre": f"{g.cliente.nombres or ''} {g.cliente.apellidos or ''}".strip(),
        "premio":         g.premio.nombre if g.premio else "-",
        "fecha":          str(g.fecha_participacion),
    } for g in ganadores]

    return {
        "ruleta": {
            "ruleta_id":               ruleta.id,
            "ruleta_nombre":           ruleta.nombre,
            "total_clientes":          total_clientes,
            "total_participaciones":   total_participaciones,
            "porcentaje_participacion": porc_global,
            "premios_entregados":      premios_entregados,
            "premios_disponibles":     premios_disponibles,
        },
        "agencias":  stats_agencias,
        "ganadores": lista_ganadores,
    }
