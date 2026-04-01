"""
=====================================================
CONFIGURACIÓN CENTRAL DE LA APLICACIÓN
=====================================================
Descripción: Lee y valida todas las variables de
             entorno usando Pydantic BaseSettings.
             Se importa desde cualquier módulo que
             necesite configuración.

Uso:
    from app.config import settings
    print(settings.DATABASE_URL)
=====================================================
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """
    Clase de configuración que carga automáticamente
    las variables desde el archivo .env
    """

    # ── Base de datos ──────────────────────────────
    DATABASE_URL: str = "postgresql://postgres:Conejo.30@localhost:8080/ruleta_db"

    # ── Servidor ───────────────────────────────────
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    APP_DEBUG: bool = True
    APP_RELOAD: bool = True

    # ── Correo SMTP ────────────────────────────────
    MAIL_USERNAME: str = "yohandercartagena@gmail.com"
    MAIL_PASSWORD: str = "qromocdlnkhtwbht"
    MAIL_FROM: str = "yohandercartagena@gmail.com"
    MAIL_FROM_NAME: str = "Ruleta de Premios"
    MAIL_PORT: int = 587
    MAIL_SERVER: str = "smtp.gmail.com"
    MAIL_TLS: bool = True
    MAIL_SSL: bool = False
    MAIL_LOTE_SIZE: int = 500  # Tamaño del lote para envío masivo (req. #5)

    # ── Seguridad ──────────────────────────────────
    SECRET_KEY: str = "dev-secret-key-cambiar-en-produccion"
    JWT_SECRET_KEY: str = "jwt-secret-key-muy-segura-para-produccion"
    TOKEN_LENGTH: int = 32  # Longitud del token único de cliente (req. #4)

    # ── Paginación ─────────────────────────────────
    PAGE_SIZE: int = 20  # Registros por página (requerimiento Semana 1)

    class Config:
        # Leer variables desde el archivo .env
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# ─────────────────────────────────────────────────────────
# Instancia única con caché - se crea una sola vez
# lru_cache evita releer el .env en cada petición
# ─────────────────────────────────────────────────────────
@lru_cache()
def get_settings() -> Settings:
    return Settings()


# Instancia global lista para importar directamente
settings = get_settings()
