"""Configuración aislada de pruebas: SQLite temporal y MongoDB simulado."""

import os
import mongomock
import pytest

os.environ["SECRET_KEY"] = "solo-pruebas-clave-segura-32-caracteres-minimo"
os.environ["OPERATIONAL_DATABASE_URL"] = "sqlite://"
os.environ["CATALOG_DATABASE_URL"] = "sqlite://"
os.environ["MONGO_URI"] = "mongodb://127.0.0.1:27017"
os.environ["MONGO_DNS_SERVERS"] = ""
os.environ["SESSION_COOKIE_SECURE"] = "0"
os.environ["CORS_ORIGIN"] = "http://localhost:5173,http://127.0.0.1:5173"


@pytest.fixture(autouse=True)
def mongo_store(monkeypatch):
    """Aísla las colecciones Mongo por prueba y evita conexiones externas."""
    cliente = mongomock.MongoClient()
    bases = {
        "users": cliente["bimetrics_users_test"],
        "activity": cliente["bimetrics_nosql_test"],
    }

    def obtener_base(dominio="activity"):
        return bases["users" if dominio == "users" else "activity"]

    for modulo in (
        "app.database",
        "app",
        "app.services.usuarios_mongo",
        "app.services.actividades_bim",
    ):
        monkeypatch.setattr(f"{modulo}.get_mongo_db", obtener_base)

    from app.database import operational_engine
    from app.models import meta

    meta.drop_all(operational_engine)
    meta.create_all(operational_engine)
    yield {**bases, "cliente": cliente}
    cliente.close()
