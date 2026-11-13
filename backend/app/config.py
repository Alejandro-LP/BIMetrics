"""Configuración central. Se puede sobrescribir con variables de entorno o un archivo .env."""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]  
load_dotenv(BASE_DIR / ".env")

DATA_DIR = BASE_DIR / "data"


def _mysql_catalog_url():
    """Construye la URL MySQL del catálogo maestro."""
    from urllib.parse import quote_plus

    user = quote_plus(os.getenv("MYSQL_USER", "root"))
    password = quote_plus(os.getenv("MYSQL_PASSWORD", ""))
    host = os.getenv("MYSQL_HOST", "localhost")
    port = os.getenv("MYSQL_PORT", "3306")
    database = os.getenv("MYSQL_DATABASE", "BIMetricsBD")
    return f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}?charset=utf8mb4"


_legacy_database_url = os.getenv("DATABASE_URL") or os.getenv("DB_URL")
_catalog_database_url = os.getenv("CATALOG_DATABASE_URL") or (
    _legacy_database_url if (_legacy_database_url or "").startswith("mysql+pymysql://")
    else _mysql_catalog_url()
)
if _catalog_database_url.startswith("mysql://"):
    _catalog_database_url = _catalog_database_url.replace("mysql://", "mysql+pymysql://", 1)
if _catalog_database_url.startswith("mysql") and "charset=" not in _catalog_database_url.lower():
    _separator = "&" if "?" in _catalog_database_url else "?"
    _catalog_database_url = f"{_catalog_database_url}{_separator}charset=utf8mb4"
CATALOG_DATABASE_URL = _catalog_database_url
OPERATIONAL_DATABASE_URL = os.getenv("OPERATIONAL_DATABASE_URL")
if not OPERATIONAL_DATABASE_URL:
    # DATABASE_URL conserva compatibilidad con instalaciones locales SQLite.
    OPERATIONAL_DATABASE_URL = (
        _legacy_database_url if (_legacy_database_url or "").startswith("sqlite")
        else f"sqlite:///{(DATA_DIR / 'presupuestos.db').as_posix()}"
    )
CORS_ORIGIN = os.getenv(
    "CORS_ORIGIN",
    "http://localhost:5173,http://127.0.0.1:5173",
)
SECRET_KEY = os.getenv("SECRET_KEY")
ROLES = {"arquitecto", "ingeniero", "administrador", "cliente"}
APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:5173").rstrip("/")
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USERNAME)
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "1").strip().lower() in {"1", "true", "yes"}
PASSWORD_RESET_DEBUG = os.getenv("PASSWORD_RESET_DEBUG", "0").strip() == "1"

# Configuración NoSQL (MongoDB) para telemetría, logs BIM e importaciones
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "bimetrics_users")
MONGO_ACTIVITY_DB_NAME = os.getenv("MONGO_ACTIVITY_DB_NAME", "bimetrics_nosql")
MONGO_DNS_SERVERS = tuple(
    servidor.strip() for servidor in os.getenv("MONGO_DNS_SERVERS", "").split(",") if servidor.strip()
)
