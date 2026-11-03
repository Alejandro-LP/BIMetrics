"""Carga un proyecto y presupuesto de demostración en SQLite y MongoDB.

Uso desde backend/: ``python -m scripts.poblar_bd --reset``.
Los importes son ilustrativos y no representan una cotización oficial.
"""

import argparse
import os
import secrets
from datetime import datetime, timezone

from pymongo import ASCENDING, MongoClient, ReturnDocument
from sqlalchemy import inspect, text
from werkzeug.security import generate_password_hash

from app.config import MONGO_DB_NAME, MONGO_URI
from app.database import operational_engine
from app.models import TABLAS, meta

INSUMOS = [
    ("Concreto premezclado 3000 PSI", "m³", 485000, 0.95),
    ('Acero corrugado 1/2"', "varilla", 46500, 8),
    ('Acero corrugado 3/8"', "varilla", 30000, 10),
    ("Alambre negro calibre 18", "kg", 7800, 3),
    ("Oficial de construcción", "jornal", 115000, 2),
    ("Ayudante de obra", "jornal", 75000, 3),
]


def _obtener_usuario_demo():
    """Busca o crea en MongoDB el perfil usado como propietario de la demo."""
    with MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000, appname="BIMetrics-DemoSeeder") as client:
        database = client[MONGO_DB_NAME]
        usuarios = database["usuarios"]
        usuarios.create_index([("id_usuario", ASCENDING)], unique=True, name="uq_usuario_id")
        usuarios.create_index([("email", ASCENDING)], unique=True, name="uq_usuario_email")
        email = "demo@bimetrics.local"
        existente = usuarios.find_one({"email": email}, {"id_usuario": 1})
        if existente:
            return existente["id_usuario"]

        contador = database["contadores"].find_one_and_update(
            {"_id": "id_usuario"},
            {"$inc": {"valor": 1}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        id_usuario = contador["valor"]
        ahora = datetime.now(timezone.utc)
        usuarios.insert_one(
            {
                "id_usuario": id_usuario,
                "nombre_completo": "Equipo de demostración",
                "email": email,
                "rol": "arquitecto",
                "password_hash": generate_password_hash(secrets.token_urlsafe(32)),
                "preferencias": {},
                "autorizacion_datos": {"aceptada": True, "version": "demo", "fecha": ahora},
                "fecha_creacion": ahora,
                "fecha_actualizacion": ahora,
            }
        )
        return id_usuario


def main(reset: bool):
    """Puebla la base operativa y asegura la identidad demo en MongoDB."""
    meta.create_all(operational_engine)
    if "ciudad" not in {columna["name"] for columna in inspect(operational_engine).get_columns("PROYECTOS")}:
        with operational_engine.begin() as connection:
            connection.execute(text("ALTER TABLE PROYECTOS ADD COLUMN ciudad VARCHAR(100)"))

    if not reset:
        with operational_engine.connect() as connection:
            if connection.execute(text("SELECT COUNT(*) FROM PROYECTOS")).scalar():
                print("Ya existen datos. Usa --reset para reemplazarlos por la demo.")
                return

    id_usuario = _obtener_usuario_demo()
    with operational_engine.begin() as connection:
        if reset:
            for tabla in reversed(TABLAS):
                connection.execute(text(f"DELETE FROM {tabla}"))

        proyecto = connection.execute(
            text("INSERT INTO PROYECTOS (id_usuario, nombre_obra, cliente, ciudad) "
                 "VALUES (:usuario, :obra, :cliente, :ciudad)"),
            {
                "usuario": id_usuario,
                "obra": "Viga entre zapatas - 10 m",
                "cliente": "Proyecto de demostración",
                "ciudad": "Bogotá",
            },
        )
        presupuesto = connection.execute(
            text("INSERT INTO PRESUPUESTOS (id_proyecto, fecha_calculo, costo_total) "
                 "VALUES (:proyecto, CURRENT_DATE, 0)"),
            {"proyecto": proyecto.lastrowid},
        )

        total = 0
        for nombre, unidad, precio, cantidad in INSUMOS:
            insumo = connection.execute(
                text("INSERT INTO INSUMOS (nombre_insumo, unidad_medida, costo_unitario) "
                     "VALUES (:nombre, :unidad, :precio)"),
                {"nombre": nombre, "unidad": unidad, "precio": precio},
            )
            connection.execute(
                text("INSERT INTO PRECIOS_CIUDAD (id_insumo, ciudad, costo_unitario) "
                     "VALUES (:insumo, :ciudad, :precio)"),
                {"insumo": insumo.lastrowid, "ciudad": "Bogotá", "precio": precio},
            )
            total += cantidad * precio
            connection.execute(
                text("INSERT INTO DETALLE_PRESUPUESTO "
                     "(id_presupuesto, id_insumo, cantidad, costo_unitario_aplicado) "
                     "VALUES (:presupuesto, :insumo, :cantidad, :precio)"),
                {
                    "presupuesto": presupuesto.lastrowid,
                    "insumo": insumo.lastrowid,
                    "cantidad": cantidad,
                    "precio": precio,
                },
            )
        connection.execute(
            text("UPDATE PRESUPUESTOS SET costo_total=:total WHERE id_presupuesto=:id"),
            {"total": total, "id": presupuesto.lastrowid},
        )

    with operational_engine.connect() as connection:
        conteo = {
            tabla: connection.execute(text(f"SELECT COUNT(*) FROM {tabla}")).scalar()
            for tabla in TABLAS
        }
    destino = (
        os.path.abspath(operational_engine.url.database)
        if operational_engine.url.get_backend_name() == "sqlite"
        else operational_engine.url.render_as_string(hide_password=True)
    )
    print(f"Demo creada: viga entre zapatas; total ${total:,.0f} COP.")
    print("Registros:", ", ".join(f"{tabla}: {cantidad}" for tabla, cantidad in conteo.items()))
    print("Ubicación:", destino)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Carga datos de demostración de BIMetrics")
    parser.add_argument("--reset", action="store_true", help="borra datos operativos antes de cargar la demo")
    main(parser.parse_args().reset)
