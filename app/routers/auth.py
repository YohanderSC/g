"""
=====================================================
ROUTER - AUTENTICACIÓN ADMIN
=====================================================
Endpoints:
  POST /auth/login                → Iniciar sesión
  GET  /auth/me                   → Perfil del admin actual
  POST /auth/cambiar-password     → Cambiar contraseña propia
  GET  /auth/admins               → Listar admins (solo superadmin)
  POST /auth/admins               → Crear nuevo admin (solo superadmin)
  PATCH /auth/admins/{id}         → Editar admin (solo superadmin)
  DELETE /auth/admins/{id}        → Eliminar admin (solo superadmin)
=====================================================
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from typing import Optional
from sqlalchemy.orm import Session
from datetime import datetime

from app.database.database import get_db
from app.models.admin_model import Administrador
from app.services.auth_service import (
    login, get_admin_actual, hashear_password, verificar_password
)

router = APIRouter(prefix="/auth", tags=["Autenticación Admin"])


# ── Schemas ───────────────────────────────────────
class LoginRequest(BaseModel):
    username: str
    password: str

class CambiarPasswordRequest(BaseModel):
    password_actual: str
    password_nueva:  str
    confirmar:       str

class AdminCreate(BaseModel):
    username:   str
    email:      EmailStr
    nombre:     Optional[str] = None
    password:   str
    superadmin: bool = False

class AdminUpdate(BaseModel):
    nombre:     Optional[str]  = None
    email:      Optional[str]  = None
    activo:     Optional[bool] = None
    superadmin: Optional[bool] = None


# ── ENDPOINT: Login ───────────────────────────────
@router.post("/login", summary="Iniciar sesión como administrador")
def admin_login(datos: LoginRequest, db: Session = Depends(get_db)):
    """
    Autentica al administrador y devuelve un token JWT.
    El token debe enviarse en el header: Authorization: Bearer {token}
    """
    return login(db, datos.username, datos.password)


# ── ENDPOINT: Perfil actual ───────────────────────
@router.get("/me", summary="Obtener perfil del admin autenticado")
def mi_perfil(admin: Administrador = Depends(get_admin_actual)):
    return {
        "id":          admin.id,
        "username":    admin.username,
        "nombre":      admin.nombre,
        "email":       admin.email,
        "superadmin":  admin.superadmin,
        "ultimo_login": str(admin.ultimo_login) if admin.ultimo_login else None,
    }


# ── ENDPOINT: Cambiar contraseña propia ──────────
@router.post("/cambiar-password", summary="Cambiar contraseña propia")
def cambiar_password(
    datos: CambiarPasswordRequest,
    admin: Administrador = Depends(get_admin_actual),
    db:    Session       = Depends(get_db),
):
    if not verificar_password(datos.password_actual, admin.password_hash):
        raise HTTPException(status_code=400, detail="La contraseña actual es incorrecta.")
    if datos.password_nueva != datos.confirmar:
        raise HTTPException(status_code=400, detail="Las contraseñas nuevas no coinciden.")
    if len(datos.password_nueva) < 6:
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 6 caracteres.")

    admin.password_hash = hashear_password(datos.password_nueva)
    db.commit()
    return {"mensaje": "Contraseña actualizada correctamente ✅"}


# ── ENDPOINT: Listar admins (solo superadmin) ─────
@router.get("/admins", summary="Listar administradores (solo superadmin)")
def listar_admins(
    admin: Administrador = Depends(get_admin_actual),
    db:    Session       = Depends(get_db),
):
    if not admin.superadmin:
        raise HTTPException(status_code=403, detail="Solo el superadmin puede gestionar administradores.")
    admins = db.query(Administrador).order_by(Administrador.id).all()
    return [{
        "id":          a.id,
        "username":    a.username,
        "nombre":      a.nombre,
        "email":       a.email,
        "activo":      a.activo,
        "superadmin":  a.superadmin,
        "ultimo_login": str(a.ultimo_login) if a.ultimo_login else None,
    } for a in admins]


# ── ENDPOINT: Crear admin ─────────────────────────
@router.post("/admins", status_code=201, summary="Crear administrador (solo superadmin)")
def crear_admin(
    datos: AdminCreate,
    admin: Administrador = Depends(get_admin_actual),
    db:    Session       = Depends(get_db),
):
    if not admin.superadmin:
        raise HTTPException(status_code=403, detail="Solo el superadmin puede crear administradores.")

    # Verificar duplicados
    if db.query(Administrador).filter(Administrador.username == datos.username).first():
        raise HTTPException(status_code=409, detail=f"El username '{datos.username}' ya existe.")
    if db.query(Administrador).filter(Administrador.email == str(datos.email)).first():
        raise HTTPException(status_code=409, detail=f"El email '{datos.email}' ya está registrado.")

    nuevo = Administrador(
        username      = datos.username,
        email         = str(datos.email),
        nombre        = datos.nombre,
        password_hash = hashear_password(datos.password),
        superadmin    = datos.superadmin,
        activo        = True,
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return {"mensaje": f"Administrador '{datos.username}' creado correctamente.", "id": nuevo.id}


# ── ENDPOINT: Editar admin ────────────────────────
@router.patch("/admins/{admin_id}", summary="Editar administrador (solo superadmin)")
def editar_admin(
    admin_id: int,
    datos:    AdminUpdate,
    admin:    Administrador = Depends(get_admin_actual),
    db:       Session       = Depends(get_db),
):
    if not admin.superadmin:
        raise HTTPException(status_code=403, detail="Solo el superadmin puede editar administradores.")

    objetivo = db.query(Administrador).filter(Administrador.id == admin_id).first()
    if not objetivo:
        raise HTTPException(status_code=404, detail=f"Admin {admin_id} no encontrado.")

    for campo, valor in datos.model_dump(exclude_unset=True).items():
        setattr(objetivo, campo, valor)

    db.commit()
    return {"mensaje": f"Admin '{objetivo.username}' actualizado correctamente."}


# ── ENDPOINT: Eliminar admin ──────────────────────
@router.delete("/admins/{admin_id}", summary="Eliminar administrador (solo superadmin)")
def eliminar_admin(
    admin_id: int,
    admin:    Administrador = Depends(get_admin_actual),
    db:       Session       = Depends(get_db),
):
    if not admin.superadmin:
        raise HTTPException(status_code=403, detail="Solo el superadmin puede eliminar administradores.")
    if admin_id == admin.id:
        raise HTTPException(status_code=400, detail="No puedes eliminarte a ti mismo.")

    objetivo = db.query(Administrador).filter(Administrador.id == admin_id).first()
    if not objetivo:
        raise HTTPException(status_code=404, detail=f"Admin {admin_id} no encontrado.")

    db.delete(objetivo)
    db.commit()
    return {"mensaje": f"Admin '{objetivo.username}' eliminado."}
