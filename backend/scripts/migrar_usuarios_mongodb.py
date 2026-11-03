"""Migra usuarios del esquema SQL anterior a la colección MongoDB nueva.

Configura ``LEGACY_USERS_DATABASE_URL`` y ejecuta desde ``backend/``:
``python -m scripts.migrar_usuarios_mongodb``.
La migración es idempotente, conserva hashes de contraseña e IDs y no borra el origen.
"""

import os
from datetime import datetime, timezone

from pymongo import ASCENDING, MongoClient
from sqlalchemy import create_engine, inspect, text

from app.config import MONGO_DB_NAME, MONGO_URI


def main():
    """Copia perfiles SQL heredados a Mongo y sincroniza el contador de IDs."""
    legacy_url = os.getenv("LEGACY_USERS_DATABASE_URL")
    if not legacy_url:
        raise RuntimeError("Define LEGACY_USERS_DATABASE_URL para identificar la base SQL de origen.")

    legacy_engine = create_engine(legacy_url, pool_pre_ping=True)
    if not inspect(legacy_engine).has_table("USUARIOS"):
        raise RuntimeError("La base indicada no contiene la tabla USUARIOS.")

    with legacy_engine.connect() as connection:
        usuarios = connection.execute(
            text("SELECT id_usuario, nombre_completo, email, rol FROM USUARIOS ORDER BY id_usuario")
        ).mappings().all()
        tiene_credenciales = inspect(legacy_engine).has_table("CREDENCIALES")
        tiene_autorizaciones = inspect(legacy_engine).has_table("AUTORIZACIONES_DATOS")
        credenciales = {}
        autorizaciones = {}
        if tiene_credenciales:
            credenciales = {
                fila["id_usuario"]: fila["password_hash"]
                for fila in connection.execute(text("SELECT id_usuario, password_hash FROM CREDENCIALES"))
            }
        if tiene_autorizaciones:
            autorizaciones = {
                fila["id_usuario"]: fila
                for fila in connection.execute(
                    text("SELECT id_usuario, version_politica, fecha_autorizacion "
                         "FROM AUTORIZACIONES_DATOS ORDER BY id_autorizacion")
                ).mappings()
            }

    migrados = 0
    existentes = 0
    with MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000, appname="BIMetrics-UserMigration") as client:
        database = client[MONGO_DB_NAME]
        collection = database["usuarios"]
        collection.create_index([("id_usuario", ASCENDING)], unique=True, name="uq_usuario_id")
        collection.create_index([("email", ASCENDING)], unique=True, name="uq_usuario_email")

        for usuario in usuarios:
            id_usuario = usuario["id_usuario"]
            existente = collection.find_one(
                {"$or": [{"id_usuario": id_usuario}, {"email": usuario["email"]}]}
            )
            if existente:
                if existente.get("id_usuario") != id_usuario or existente.get("email") != usuario["email"]:
                    raise RuntimeError("Se detectó un conflicto de ID o correo; revisa los registros antes de continuar.")
                existentes += 1
                continue

            ahora = datetime.now(timezone.utc)
            autorizacion = autorizaciones.get(id_usuario)
            collection.insert_one(
                {
                    "id_usuario": id_usuario,
                    "nombre_completo": usuario["nombre_completo"],
                    "email": usuario["email"],
                    "rol": usuario["rol"],
                    "password_hash": credenciales.get(id_usuario),
                    "preferencias": {},
                    "autorizacion_datos": {
                        "aceptada": bool(autorizacion),
                        "version": autorizacion["version_politica"] if autorizacion else None,
                        "fecha": autorizacion["fecha_autorizacion"] if autorizacion else None,
                    },
                    "fecha_creacion": ahora,
                    "fecha_actualizacion": ahora,
                }
            )
            migrados += 1

        max_id = max((usuario["id_usuario"] for usuario in usuarios), default=0)
        database["contadores"].update_one(
            {"_id": "id_usuario"}, {"$max": {"valor": max_id}}, upsert=True
        )

    legacy_engine.dispose()
    print(f"Usuarios migrados: {migrados}; ya existentes: {existentes}.")


if __name__ == "__main__":
    main()
