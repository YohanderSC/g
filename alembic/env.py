"""
=====================================================
ALEMBIC - ENTORNO DE MIGRACIONES
=====================================================
Descripción: Conecta Alembic con los modelos ORM
             de SQLAlchemy para generar migraciones
             automáticas con --autogenerate.

Modo de uso:
  # Crear nueva migración automática:
  alembic revision --autogenerate -m "descripcion del cambio"

  # Aplicar todas las migraciones pendientes:
  alembic upgrade head

  # Revertir la última migración:
  alembic downgrade -1

  # Ver historial de migraciones:
  alembic history --verbose

  # Ver estado actual:
  alembic current
=====================================================
"""

from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import os
import sys

# Agregar el directorio raíz al path para importar los módulos del proyecto
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importar la Base y todos los modelos para que Alembic los detecte
# Es IMPORTANTE importar los modelos aquí para que autogenerate los incluya
from app.database.database import Base
from app.models import models  # noqa: F401 - importar para registrar todos los modelos

# Configuración de Alembic leída desde alembic.ini
config = context.config

# Configurar logging desde el archivo alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata de los modelos - Alembic la usa para detectar cambios
target_metadata = Base.metadata

# ─────────────────────────────────────────────────────────
# Leer DATABASE_URL desde variable de entorno si existe
# Esto permite usar el mismo alembic.ini en distintos entornos
# ─────────────────────────────────────────────────────────
database_url = os.getenv("DATABASE_URL")
if database_url:
    # Sobreescribir la URL del alembic.ini con la del entorno
    config.set_main_option("sqlalchemy.url", database_url)


def run_migrations_offline() -> None:
    """
    Modo OFFLINE: genera SQL sin conectarse a la BD.
    Útil para revisar el SQL antes de ejecutarlo.
    Ejecutar con: alembic upgrade head --sql
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,           # Detectar cambios de tipo de columna
        compare_server_default=True, # Detectar cambios de valores por defecto
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Modo ONLINE: conecta a la BD y aplica los cambios directamente.
    Es el modo por defecto cuando se ejecuta alembic upgrade.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,   # Sin pool en migraciones para evitar conexiones colgadas
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,           # Detectar cambios de tipo de columna
            compare_server_default=True, # Detectar cambios de valores por defecto
        )

        with context.begin_transaction():
            context.run_migrations()


# Ejecutar el modo correspondiente según el contexto
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
