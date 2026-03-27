"""
Sistema de Ruleta de Premios — v3.2
main.py con autenticación JWT para el panel admin
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import os

from app.database.database import engine, Base, SessionLocal
from app.models import models            # noqa
from app.models import referido_model_orm  # noqa
from app.models import admin_model       # noqa — registra tabla administradores
from app.models import encuesta_model    # noqa — registra tablas encuesta

from app.routers import ruletas, clientes, premios, agencias, preguntas
from app.routers import encuestas
from app.routers import ruleta_giro, referidos, auth

Base.metadata.create_all(bind=engine)

# Crear admin inicial si no existe ninguno
from app.services.auth_service import crear_admin_inicial
db = SessionLocal()
try:
    crear_admin_inicial(db)
finally:
    db.close()

app = FastAPI(
    title="API Sistema de Ruleta de Premios",
    version="3.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    __import__('fastapi.middleware.cors', fromlist=['CORSMiddleware']).CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

# Routers
app.include_router(auth.router)          # /auth/login etc. — SIN protección
app.include_router(ruletas.router)
app.include_router(clientes.router)
app.include_router(premios.router)
app.include_router(agencias.router)
app.include_router(preguntas.router)
app.include_router(ruleta_giro.router)
app.include_router(referidos.router)
app.include_router(encuestas.router)

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend")

@app.get("/frontend", include_in_schema=False)
def frontend():
    ruta = os.path.join(FRONTEND_DIR, "ruleta.html")
    return FileResponse(ruta, media_type="text/html") if os.path.exists(ruta) \
        else {"error": "ruleta.html no encontrado"}

@app.get("/admin", include_in_schema=False)
def admin_panel():
    ruta = os.path.join(FRONTEND_DIR, "admin.html")
    return FileResponse(ruta, media_type="text/html") if os.path.exists(ruta) \
        else {"error": "admin.html no encontrado"}

@app.get("/login", include_in_schema=False)
def login_page():
    ruta = os.path.join(FRONTEND_DIR, "login.html")
    return FileResponse(ruta, media_type="text/html") if os.path.exists(ruta) \
        else {"error": "login.html no encontrado"}

@app.get("/", tags=["Estado"])
def root():
    return {
        "app": "Sistema de Ruleta de Premios",
        "version": "3.2.0", "estado": "activa ✅",
        "docs": "/docs", "frontend": "/frontend",
        "admin": "/admin", "login": "/login",
    }
