"""
=====================================================
APLICACIÓN PRINCIPAL - SISTEMA DE RULETA DE PREMIOS
=====================================================
Versión: 2.0 (Semana 2)
Módulos: Ruletas, Clientes, Premios, Agencias,
         Preguntas de Seguridad
=====================================================
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database.database import engine, Base
from app.models import models  # noqa: F401 - registra todos los modelos ORM

# Importar routers
from app.routers import ruletas
from app.routers import clientes
from app.routers import premios
from app.routers import agencias
from app.routers import preguntas

# Crear tablas si no existen (en producción usar Alembic)
Base.metadata.create_all(bind=engine)

# ─────────────────────────────────────────────────────────
# INSTANCIA FASTAPI
# ─────────────────────────────────────────────────────────
app = FastAPI(
    title="API Sistema de Ruleta de Premios",
    description="""
API REST para gestión de eventos de ruleta de premios.

## Módulos disponibles

- **RULETAS** — CRUD completo con paginación
- **CLIENTES** — CRUD + importación masiva XLSX/CSV + búsqueda por email
- **PREMIOS** — CRUD + control de inventario + premios condicionados
- **AGENCIAS** — CRUD completo
- **PREGUNTAS DE SEGURIDAD** — CRUD completo
- **CORREOS** — Envío individual y masivo en lotes de 500 *(Semana 3)*
- **RULETA (GIRO)** — Lógica de asignación aleatoria *(Semana 3)*
- **VAMOS CON TODO HERMANITO LUIS** 
    """,
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ─────────────────────────────────────────────────────────
# CORS
# ─────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────────────────
# ROUTERS
# ─────────────────────────────────────────────────────────
app.include_router(ruletas.router)    # /ruletas/
app.include_router(clientes.router)   # /clientes/
app.include_router(premios.router)    # /premios/
app.include_router(agencias.router)   # /agencias/
app.include_router(preguntas.router)  # /preguntas/


# ─────────────────────────────────────────────────────────
# HEALTH CHECK
# ─────────────────────────────────────────────────────────
@app.get("/", tags=["Estado"])
def root():
    return {
        "app":     "Sistema de Ruleta de Premios",
        "version": "2.0.0",
        "estado":  "activa ✅",
        "docs":    "/docs",
        "modulos": ["ruletas", "clientes", "premios", "agencias", "preguntas"],
    }
