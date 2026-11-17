"""Demostración de la sustentación con datos ficticios y bases aisladas."""
import json
import os
import sys
from pathlib import Path
from uuid import uuid4
from unittest.mock import patch

import mongomock
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
os.environ.update(
    BIMETRICS_ENV="development",
    SECRET_KEY=uuid4().hex,
    OPERATIONAL_DATABASE_URL="sqlite://",
    CATALOG_DATABASE_URL="sqlite://",
    MONGO_URI="mongodb://127.0.0.1:27017",
    MONGO_DNS_SERVERS="",
    SESSION_COOKIE_SECURE="0",
    CORS_ORIGIN="http://localhost:5173",
    PASSWORD_RESET_DEBUG="0",
)

from app import create_app
from app.database import operational_engine
from app.services.usuarios_mongo import _coleccion

ORIGIN = {"Origin": "http://localhost:5173"}

def request(client, method, route, expected, payload=None):
    response = client.open(route, method=method, json=payload, headers=ORIGIN)
    if response.status_code != expected:
        raise RuntimeError(f"{method} {route}: HTTP {response.status_code}, esperado {expected}")
    return response

def show(label, value):
    print(label, flush=True)
    print(json.dumps(value, ensure_ascii=False, indent=2), flush=True)

def account(client, name, role):
    data = {"nombre_completo": name, "email": role+"@bimetrics.test",
            "password": uuid4().hex, "rol": role, "autoriza_datos": True}
    user = request(client, "POST", "/api/auth/registro", 201, data).json
    request(client, "POST", "/api/auth/logout", 200)
    request(client, "POST", "/api/auth/login", 200, data)
    return user

def main():
    with mongomock.MongoClient() as mongo:
        def demo_db(domain="activity"):
            return mongo["sustentacion_" + domain]

        with (
            patch("app.get_mongo_db", demo_db),
            patch("app.database.get_mongo_db", demo_db),
            patch("app.services.usuarios_mongo.get_mongo_db", demo_db),
            patch("app.services.actividades_bim.get_mongo_db", demo_db),
        ):
            server = create_app()
            admin, customer = server.test_client(), server.test_client()
            owner = account(admin, "Equipo de demostración", "arquitecto")
            account(customer, "Cliente de demostración", "cliente")
            with server.app_context():
                _coleccion().update_one({"id_usuario": owner["id_usuario"]}, {"$set": {"rol": "administrador"}})
            project = request(admin, "POST", "/api/proyectos", 201, {"nombre_obra": "Edificio Norte · Demo", "ciudad": "Bogotá"}).json
            pid = project["id_proyecto"]
            part = {"codigo": "DEMO-01", "descripcion": "Tubería de refrigeración", "unidad": "m", "precio_defecto": 45000}
            request(admin, "POST", "/api/partidas", 201, part)
            budget = request(admin, "POST", "/api/presupuestos", 201, {
                "id_proyecto": pid, "aiu": {"administracion": 10, "imprevistos": 3, "utilidad": 7},
            }).json
            bid = budget["id_presupuesto"]
            request(admin, "POST", f"/api/presupuestos/{bid}/partidas", 201, {"codigo": part["codigo"], "cantidad": 20})
            with operational_engine.connect() as connection:
                stored = connection.execute(text(
                    "SELECT id_proyecto, id_presupuesto, costo_total FROM PRESUPUESTOS WHERE id_presupuesto = :id"
                ), {"id": bid}).mappings().one()
            consulted = request(admin, "GET", f"/api/presupuestos/{bid}", 200).json
            assert float(stored["costo_total"]) == float(consulted["costo_total"]) == 1080000
            show("01 · SQL | Registro almacenado y total consultado por API", {
                "tabla_PRESUPUESTOS": dict(stored), "consulta_http": 200, "total_consultado": consulted["costo_total"],
            })
            created = request(admin, "POST", "/api/actividades-bim", 201, {
                "id_usuario": owner["id_usuario"], "id_proyecto": pid, "tipo_evento": "revision_bim",
                "software_origen": "Revit", "nombre_archivo": "cantidades-prueba.txt", "estado": "completado",
                "detalles_bim": {"num_elementos": 2, "unidades": ["m"]},
            }).json
            stored_event = demo_db()["actividades_bim"].find_one({"id_proyecto": pid})
            fetched = request(admin, "GET", f"/api/actividades-bim/{created['id']}", 200).json
            assert str(stored_event["_id"]) == fetched["id"]
            show("02 · NoSQL | Documento almacenado y consultado", {
                "coleccion": "actividades_bim", "id_proyecto": stored_event["id_proyecto"],
                "detalles_bim": stored_event["detalles_bim"], "consulta_http": 200,
            })
            summary = request(admin, "GET", "/api/dashboard/resumen", 200).json["resumen"]
            assert summary["ultima_actividad_bim"]["id"] == created["id"]
            show("03 · Resumen | SQL y MongoDB simulado", {
                "total_proyectos": summary["total_proyectos"], "presupuesto_total": summary["presupuesto_total"],
                "ultima_actividad_bim": summary["ultima_actividad_bim"]["tipo_evento"],
            })
            new_part = {**part, "codigo": "DEMO-ROL"}
            denied = request(customer, "POST", "/api/partidas", 403, new_part)
            allowed = request(admin, "POST", "/api/partidas", 201, new_part)
            show("04 · Perfiles | La misma petición POST /api/partidas", {
                "cliente": {"http": denied.status_code, "respuesta": denied.json},
                "administrador": {"http": allowed.status_code, "codigo_creado": allowed.json["codigo"]},
            })

if __name__ == "__main__":
    main()

