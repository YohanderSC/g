"""
=====================================================
APLICACIÓN PRINCIPAL - SISTEMA DE RULETA DE PREMIOS
=====================================================
Descripción: Punto de entrada de la API REST.
             Configura FastAPI, registra los routers,
             aplica middlewares y crea las tablas al iniciar.
=====================================================
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database.database import engine, Base
from app.routers import ruletas

# Importar todos los modelos para que SQLAlchemy los registre
# y cree las tablas correctamente al ejecutar create_all
from app.models import models  # noqa: F401

# ─────────────────────────────────────────────────────────
# CREAR TABLAS EN LA BASE DE DATOS
# Se ejecuta al iniciar la aplicación si las tablas no existen.
# En producción se recomienda usar Alembic en lugar de create_all.
# ─────────────────────────────────────────────────────────
Base.metadata.create_all(bind=engine)

# ─────────────────────────────────────────────────────────
# INSTANCIA DE LA APLICACIÓN FASTAPI
# ─────────────────────────────────────────────────────────
app = FastAPI(
    title="API Sistema de Ruleta de Premios",
    description="""
    API REST para gestión de eventos de ruleta de premios.

    ## Módulos disponibles
    - 🎡 **Ruletas** — CRUD completo con paginación de 20 registros por página
    - 👥 **Clientes** — Importación masiva XLSX/CSV, tokens únicos *(Semana 2)*
    - 🏆 **Premios** — Control de existencias, premios condicionados *(Semana 2)*
    - 🏢 **Agencias** — Gestión de sucursales *(Semana 2)*
    - 📧 **Correos** — Envío masivo en lotes de 500 *(Semana 2)*
    - 📊 **Reportes** — Participación y estadísticas *(Semana 2)*
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ─────────────────────────────────────────────────────────
# MIDDLEWARE CORS
# Permite peticiones desde el frontend (ajustar en producción)
# ─────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # En producción: especificar el dominio del frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────────────────
# REGISTRO DE ROUTERS
# ─────────────────────────────────────────────────────────
app.include_router(ruletas.router)   # GET/POST/PATCH/DELETE /ruletas/


# ─────────────────────────────────────────────────────────
# ENDPOINT RAÍZ — Health check
# ─────────────────────────────────────────────────────────
@app.get("/", tags=["Estado"])
def root():
    """Verifica que la API está activa y retorna información básica."""
    return {
        "app": "Sistema de Ruleta de Premios",
        "version": "1.0.0",
        "estado": "activa ✅",
        "docs": "/docs",
        "debug": settings.APP_DEBUG,
    }
