"""Crea el primer administrador de forma interactiva y fuera del registro público.

Ejecutar desde ``backend/``: ``python -m scripts.crear_administrador``.
El proceso solo funciona si todavía no existe una cuenta administradora.
"""

import getpass
import re
from datetime import datetime, timezone

from pymongo import ASCENDING, MongoClient, ReturnDocument
from werkzeug.security import generate_password_hash

from app.config import MONGO_DB_NAME, MONGO_URI


def main():
    """Verifica MongoDB, valida credenciales y crea el administrador inicial."""
    nombre = input("Nombre completo del administrador: ").strip()
    email = input("Correo del administrador: ").strip().lower()
    password = getpass.getpass("Contraseña (mínimo 12 caracteres): ")
    confirmacion = getpass.getpass("Confirma la contraseña: ")

    if not 2 <= len(nombre) <= 150:
        raise SystemExit("El nombre debe tener entre 2 y 150 caracteres.")
    if len(email) > 150 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        raise SystemExit("Escribe una dirección de correo válida.")
    if not 12 <= len(password) <= 128:
        raise SystemExit("La contraseña debe tener entre 12 y 128 caracteres.")
    if password != confirmacion:
        raise SystemExit("Las contraseñas no coinciden.")

    with MongoClient(
        MONGO_URI,
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=5000,
        appname="BIMetrics-AdminBootstrap",
    ) as client:
        client.admin.command("ping")
        database = client[MONGO_DB_NAME]
        usuarios = database["usuarios"]
        usuarios.create_index([("id_usuario", ASCENDING)], unique=True, name="uq_usuario_id")
        usuarios.create_index([("email", ASCENDING)], unique=True, name="uq_usuario_email")

        if usuarios.count_documents({"rol": "administrador"}, limit=1):
            raise SystemExit("Ya existe un administrador. Crea cuentas adicionales desde la API administrativa.")
        if usuarios.find_one({"email": email}, {"_id": 1}):
            raise SystemExit("Ese correo ya está registrado; no se modificó ninguna cuenta.")

        ultimo_usuario = usuarios.find_one(sort=[("id_usuario", -1)], projection={"id_usuario": 1})
        ultimo_id = int(ultimo_usuario.get("id_usuario", 0)) if ultimo_usuario else 0
        database["contadores"].update_one(
            {"_id": "id_usuario"}, {"$max": {"valor": ultimo_id}}, upsert=True
        )
        secuencia = database["contadores"].find_one_and_update(
            {"_id": "id_usuario"},
            {"$inc": {"valor": 1}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        ahora = datetime.now(timezone.utc)
        usuarios.insert_one({
            "id_usuario": secuencia["valor"],
            "nombre_completo": nombre,
            "email": email,
            "password_hash": generate_password_hash(password),
            "version_sesion": 1,
            "rol": "administrador",
            "preferencias": {},
            "autorizacion_datos": {"aceptada": True, "version": "2026-10-15", "fecha": ahora},
            "fecha_creacion": ahora,
            "fecha_actualizacion": ahora,
        })

    print(f"Administrador creado para {email}. La contraseña no se guardó en texto plano.")


if __name__ == "__main__":
    main()
