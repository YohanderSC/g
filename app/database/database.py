"""
=====================================================
CONFIGURACIÓN DE BASE DE DATOS
=====================================================
Descripción: Configura la conexión a PostgreSQL usando
             SQLAlchemy. Compatible con dos drivers:
               - psycopg  (v3) → recomendado en Windows
               - psycopg2 (v2) → Linux/Mac
=====================================================
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# ─────────────────────────────────────────────────────────
# URL DE CONEXIÓN
# Se lee desde la variable de entorno DATABASE_URL del .env
#
# ⚠️  IMPORTANTE según el driver instalado:
#
#   Con psycopg3  (OPCIÓN A - Windows recomendado):
#     DATABASE_URL = postgresql+psycopg://user:pass@host:5432/db
#
#   Con psycopg2  (OPCIÓN B - Linux/Mac):
#     DATABASE_URL = postgresql+psycopg2://user:pass@host:5432/db
#     o simplemente:
#     DATABASE_URL = postgresql://user:pass@host:5432/db
# ─────────────────────────────────────────────────────────
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    #"postgresql+psycopg://postgres:Conejo.30@localhost:8080/ruleta_db" 
    # jajaja lo tengo configurado asi
    #"postgresql+psycopg://postgres:postgres@localhost:5432/ruleta_db"
)

# Motor de base de datos
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,   # Verifica que la conexión esté activa antes de usarla
    pool_size=10,         # Conexiones simultáneas en el pool
    max_overflow=20,      # Conexiones extra cuando el pool está lleno
)

# Fábrica de sesiones — cada petición HTTP obtiene su propia sesión
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Clase base de la cual heredan todos los modelos ORM
Base = declarative_base()


# ─────────────────────────────────────────────────────────
# DEPENDENCIA: get_db()
# Se inyecta en cada endpoint con FastAPI Depends()
# Garantiza que la sesión se cierre al finalizar la petición
# ─────────────────────────────────────────────────────────
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
