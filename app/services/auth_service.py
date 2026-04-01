"""
=====================================================
SERVICIO DE AUTENTICACIÓN - ADMIN
=====================================================
Maneja:
  - Hasheo de contraseñas con bcrypt
  - Generación y verificación de tokens JWT
  - Login y validación de sesión
====================================================
"""

import os
import bcrypt
from datetime import datetime, timedelta
from typing import Optional
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import JWTError, jwt

from app.database.database import get_db
from app.models.admin_model import Administrador

# ── Configuración ─────────────────────────────────
# SECURITY: La SECRET_KEY debe definirse en variable de entorno
# Generar con: python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "DEV-ONLY-CHANGE-IN-PRODUCTION")
ALGORITHM = "HS256"
EXPIRE_HORAS = 8  # Sesión expira en 8 horas

bearer = HTTPBearer(auto_error=False)


# ─────────────────────────────────────────────────
# HELPERS DE CONTRASEÑA (usando bcrypt directamente)
# ─────────────────────────────────────────────────
def hashear_password(password: str) -> str:
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt).decode("utf-8")


def verificar_password(password: str, hashed: str) -> bool:
    password_bytes = password.encode("utf-8")
    hashed_bytes = hashed.encode("utf-8")
    return bcrypt.checkpw(password_bytes, hashed_bytes)


# ─────────────────────────────────────────────────
# HELPERS DE JWT
# ─────────────────────────────────────────────────
def crear_token(data: dict) -> str:
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(hours=EXPIRE_HORAS)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decodificar_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado.",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ─────────────────────────────────────────────────
# LOGIN
# ─────────────────────────────────────────────────
def login(db: Session, username: str, password: str) -> dict:
    admin = (
        db.query(Administrador)
        .filter(
            Administrador.username == username,
            Administrador.activo == True,
        )
        .first()
    )

    if not admin or not verificar_password(password, admin.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos.",
        )

    # Actualizar último login
    admin.ultimo_login = datetime.utcnow()
    db.commit()

    token = crear_token(
        {
            "sub": str(admin.id),
            "username": admin.username,
            "nombre": admin.nombre or admin.username,
            "superadmin": admin.superadmin,
        }
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": EXPIRE_HORAS * 3600,
        "admin": {
            "id": admin.id,
            "username": admin.username,
            "nombre": admin.nombre,
            "email": admin.email,
            "superadmin": admin.superadmin,
        },
    }


# ─────────────────────────────────────────────────
# DEPENDENCIA: obtener admin actual desde el token
# ─────────────────────────────────────────────────
def get_admin_actual(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: Session = Depends(get_db),
) -> Administrador:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Se requiere autenticación. Por favor inicia sesión.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decodificar_token(credentials.credentials)
    admin_id = payload.get("sub")

    admin = (
        db.query(Administrador)
        .filter(
            Administrador.id == int(admin_id),
            Administrador.activo == True,
        )
        .first()
    )

    if not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Administrador no encontrado o inactivo.",
        )
    return admin


# ─────────────────────────────────────────────────
# UTILIDAD: Crear admin inicial (se llama al arrancar)
# ─────────────────────────────────────────────────
def crear_admin_inicial(db: Session):
    """
    Crea el administrador por defecto si no existe ninguno.
    Credenciales: admin / admin123
    Cambiar inmediatamente después del primer login.
    """
    existe = db.query(Administrador).first()
    if not existe:
        admin = Administrador(
            username="admin",
            email="admin@ruleta.com",
            nombre="Administrador",
            password_hash=hashear_password("admin123"),
            superadmin=True,
            activo=True,
        )
        db.add(admin)
        db.commit()
        print("✅ Admin inicial creado — usuario: admin | contraseña: admin123")
        print("⚠️  Cambia la contraseña desde el panel después del primer login.")
