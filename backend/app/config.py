"""Configuración central. Se puede sobrescribir con variables de entorno o un archivo .env."""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]  
load_dotenv(BASE_DIR / ".env")

DATA_DIR = BASE_DIR / "data"
DB_URL = os.getenv("DATABASE_URL", f"sqlite:///{(DATA_DIR / 'presupuestos.db').as_posix()}")
CORS_ORIGIN = os.getenv("CORS_ORIGIN", "*")
SECRET_KEY = os.getenv("SECRET_KEY")
ROLES = {"arquitecto", "ingeniero", "administrador", "cliente"}

# Configuración NoSQL (MongoDB) para telemetría, logs BIM e importaciones
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "bimetrics_nosql")
