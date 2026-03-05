"""
=====================================================
SERVICIO: LÓGICA DE NEGOCIO DE CLIENTES
=====================================================
Versión   : 1.0 (portado desde proyecto Django heredado)

Este archivo centraliza la lógica de negocio que en el
proyecto antiguo (Django) estaba distribuida en:
  - funciones sueltas en models-clientes.py
  - señales pre_save de Django

FUNCIONES PORTADAS Y REFACTORIZADAS:
  generar_token()      → era método en clase Cliente (Django)
  asignar_token()      → era método en clase Cliente (Django)
  generar_premio()     → era función suelta (Django)
  gestionar_acciones() → era señal pre_save (Django)

MEJORAS APLICADAS:
  - Se eliminan listas hardcodeadas de emails condicionados
    (ahora se consultan desde la tabla premios_condicionados)
  - La lógica de randint(1, conteo) se reemplaza por
    una selección aleatoria más robusta con SQLAlchemy
  - Los correos se delegan a correo_service.py
  - Cada función recibe db (Session) como parámetro
=====================================================
"""

import uuid
import random
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.models import (
    Cliente, Premio, PremioCondicionado, EstatusCliente, CorreoLog, TipoCorreo, EstadoCorreo
)


# ─────────────────────────────────────────────────────────
# FUNCIÓN: generar_token
# Portada desde el método generar_token() de la clase Cliente en Django.
#
# Original Django:
#   def generar_token(self, n_digit):
#       cadena_aleatoria = str(uuid.uuid4())
#       token = cadena_aleatoria[:n_digit]
#       return token
#
# Cambio: se extrae como función independiente (no método de modelo)
# ─────────────────────────────────────────────────────────
def generar_token(n_digit: int = 32) -> str:
    """
    Genera un token aleatorio usando UUID4.
    Por defecto usa 32 caracteres (igual que el proyecto antiguo).

    Args:
        n_digit: Cantidad de caracteres del token (máx. 36)
    Returns:
        String con el token generado
    """
    cadena_aleatoria = str(uuid.uuid4())   # Ej: "550e8400-e29b-41d4-a716-446655440000"
    token = cadena_aleatoria[:n_digit]
    return token


# ─────────────────────────────────────────────────────────
# FUNCIÓN: asignar_token
# Portada desde el método asignar_token() de la clase Cliente en Django.
#
# Original Django:
#   def asignar_token(self):
#       nuevo_token = ''
#       for i in [30, 30, 30, 32, 32, 32, 35, 35, 35]:
#           nuevo_token = self.generar_token(i)
#           sentinel = Cliente.objects.filter(token=nuevo_token).exists()
#           if sentinel == False:
#               break
#       self.token = nuevo_token
#       return nuevo_token
#
# Cambio: recibe db Session para verificar unicidad con SQLAlchemy
# ─────────────────────────────────────────────────────────
def asignar_token(cliente: Cliente, db: Session) -> str:
    """
    Genera y asigna un token único al cliente.
    Intenta múltiples longitudes hasta encontrar uno que no exista.

    El proyecto antiguo intentaba con longitudes [30,30,30,32,32,32,35,35,35].
    Se mantiene la misma secuencia de intentos para compatibilidad.

    Args:
        cliente: instancia del modelo Cliente
        db     : sesión de base de datos SQLAlchemy
    Returns:
        El token único asignado
    """
    nuevo_token = ''

    # Misma secuencia de longitudes del proyecto antiguo
    for n_digit in [30, 30, 30, 32, 32, 32, 35, 35, 35]:
        nuevo_token = generar_token(n_digit)

        # Verificar que el token no exista ya en la BD
        # En Django era: Cliente.objects.filter(token=nuevo_token).exists()
        existe = db.query(Cliente).filter(Cliente.token == nuevo_token).first()

        if not existe:
            break   # Token único encontrado, salir del bucle

    # Asignar el token al cliente
    cliente.token = nuevo_token
    return nuevo_token


# ─────────────────────────────────────────────────────────
# FUNCIÓN: generar_premio
# Portada y refactorizada desde la función suelta generar_premio()
# del proyecto Django.
#
# MEJORAS RESPECTO AL ORIGINAL:
#   1. Las listas hardcodeadas de emails condicionados se reemplazaron
#      por consultas a la tabla premios_condicionados.
#   2. El randint(1, conteo) se reemplaza por una selección aleatoria
#      que considera la cantidad_disponible de cada premio.
#   3. Se elimina la lógica especial de "premio.id == 1" como fallback
#      hardcodeado; ahora el fallback es el primer premio disponible.
# ─────────────────────────────────────────────────────────
def generar_premio(email: str, db: Session) -> Premio | None:
    """
    Asigna un premio al cliente según las siguientes reglas (mismo flujo del antiguo):

    1. CONDICIONADO: Si el cliente tiene un premio específico reservado
       en la tabla premios_condicionados, se le asigna ese premio.

    2. ALEATORIO: Si no tiene premio condicionado, se selecciona uno
       aleatoriamente entre los disponibles (cantidad_disponible > 0),
       excluyendo los premios condicionados reservados para otros clientes.

    3. FALLBACK: Si no hay premios disponibles, retorna None.

    Args:
        email: email del cliente que va a girar la ruleta
        db   : sesión de base de datos
    Returns:
        Objeto Premio asignado, o None si no hay disponibles
    """

    # ── PASO 1: Verificar si tiene premio condicionado ──────────
    # En el proyecto antiguo esto eran listas hardcodeadas:
    #   if email in clientes_premios_unicos_1:
    #       premio = Premio.objects.get(id=premios_unicos_1[0])
    # Ahora se consulta desde la base de datos:
    premio_condicionado = (
        db.query(PremioCondicionado)
        .filter(
            PremioCondicionado.email_cliente == email,
            PremioCondicionado.entregado == False
        )
        .first()
    )

    if premio_condicionado:
        # Obtener el premio reservado para este cliente
        premio = db.query(Premio).filter(Premio.id == premio_condicionado.premio_id).first()

        if premio and premio.cantidad_disponible > 0:
            # Descontar del inventario (igual que el original: existencia-1, entregados+1)
            premio.cantidad_disponible -= 1
            premio.cantidad_entregada  += 1
            # Marcar el condicionado como entregado
            premio_condicionado.entregado = True
            db.commit()
            db.refresh(premio)
            return premio

    # ── PASO 2: Selección aleatoria ─────────────────────────────
    # Obtener IDs de premios reservados (condicionados no entregados)
    # para excluirlos de la selección aleatoria (replicando la lógica
    # del original que excluía premios_unicos_1..4)
    ids_condicionados = [
        row.premio_id for row in
        db.query(PremioCondicionado.premio_id)
        .filter(PremioCondicionado.entregado == False)
        .all()
    ]

    # Obtener premios disponibles excluyendo los condicionados
    premios_disponibles = (
        db.query(Premio)
        .filter(
            Premio.cantidad_disponible > 0,
            Premio.id.notin_(ids_condicionados) if ids_condicionados else True
        )
        .all()
    )

    if not premios_disponibles:
        # FALLBACK: si no hay premios sin condición, buscar cualquiera disponible
        # En el antiguo era: premio = Premio.objects.get(id=1) como fallback fijo
        # Aquí es más flexible: tomar el primer disponible
        premio_fallback = (
            db.query(Premio)
            .filter(Premio.cantidad_disponible > 0)
            .first()
        )
        if not premio_fallback:
            return None   # No hay premios disponibles en absoluto
        premios_disponibles = [premio_fallback]

    # Selección aleatoria entre los disponibles
    # Original usaba: rdm.randint(1, conteo) en un while loop
    # Aquí se hace directamente con random.choice sobre la lista filtrada
    premio_elegido = random.choice(premios_disponibles)

    # Descontar del inventario
    premio_elegido.cantidad_disponible -= 1
    premio_elegido.cantidad_entregada  += 1
    db.commit()
    db.refresh(premio_elegido)

    return premio_elegido


# ─────────────────────────────────────────────────────────
# FUNCIÓN: gestionar_acciones_cliente
# Portada desde la señal pre_save gestionar_acciones() de Django.
#
# Original Django (señal pre_save):
#   if instance.estatus_cliente_id is None:       → asignar token
#   if instance.estatus_cliente_id == 2:           → asignar premio
#   if instance.estatus_cliente_id == 3:           → enviar felicitación
#   if instance.estatus_cliente_id == 4:           → notificar referido
#
# En FastAPI no hay señales; esta función se llama explícitamente
# desde el servicio o el endpoint cuando el estatus del cliente cambia.
# ─────────────────────────────────────────────────────────
def gestionar_acciones_cliente(cliente: Cliente, db: Session) -> None:
    """
    Ejecuta las acciones correspondientes según el estatus actual del cliente.
    Equivale a la señal pre_save gestionar_acciones() del proyecto Django.

    Se debe llamar DESPUÉS de cambiar el estatus del cliente y ANTES del commit.

    Args:
        cliente: instancia del modelo Cliente con el estatus ya actualizado
        db     : sesión de base de datos
    """

    # ── ESTATUS: anadido ────────────────────────────────────────
    # Original: if instance.estatus_cliente_id is None → asignar token
    # Se activa cuando el cliente es recién importado/añadido
    if cliente.estatus == EstatusCliente.anadido and not cliente.token:
        asignar_token(cliente, db)

    # ── ESTATUS: registrado ─────────────────────────────────────
    # Original: if instance.estatus_cliente_id == 2 → generar premio
    # Se activa cuando el cliente completa su registro de datos
    elif cliente.estatus == EstatusCliente.registrado:
        premio = generar_premio(cliente.email, db)
        if premio:
            cliente.premio_id = premio.id

    # ── ESTATUS: participo ──────────────────────────────────────
    # Original: if instance.estatus_cliente_id == 3 → enviar felicitaciones
    # Se activa cuando el cliente gira la ruleta
    # El envío del correo se delega a correo_service.py para separar responsabilidades
    elif cliente.estatus == EstatusCliente.participo:
        # Registrar el correo pendiente de envío
        log = CorreoLog(
            cliente_id=cliente.id,
            tipo=TipoCorreo.felicitacion,
            estado=EstadoCorreo.pendiente,
            asunto="¡Felicitaciones! Ganaste en la Ruleta de Premios"
        )
        db.add(log)
        # El envío real se procesa por correo_service.py (siguiente semana)

    # ── ESTATUS: referido ───────────────────────────────────────
    # Original: if instance.estatus_cliente_id == 4 → asignar token + notificar referido
    elif cliente.estatus == EstatusCliente.referido:
        # Asignar token si no tiene
        if not cliente.token:
            asignar_token(cliente, db)
        # Registrar notificación pendiente al admin
        log = CorreoLog(
            cliente_id=cliente.id,
            tipo=TipoCorreo.referido,
            estado=EstadoCorreo.pendiente,
            asunto=f"Referido | {cliente.nombres} {cliente.apellidos or ''}"
        )
        db.add(log)

    # ── ESTATUS: referido_aprobado ──────────────────────────────
    # Original: comentado en el código antiguo (pass)
    # Se implementa para enviar invitación al referido aprobado
    elif cliente.estatus == EstatusCliente.referido_aprobado:
        log = CorreoLog(
            cliente_id=cliente.id,
            tipo=TipoCorreo.invitacion,
            estado=EstadoCorreo.pendiente,
            asunto="¡Tu invitación a la Ruleta de Premios fue aprobada!"
        )
        db.add(log)
