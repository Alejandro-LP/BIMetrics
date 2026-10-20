"""Pruebas de la API. Ejecutar desde backend/:  python -m pytest -q"""
import os
import tempfile
from unittest.mock import patch

# La base de pruebas va en una carpeta temporal, nunca en data/
os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/prueba.db"

import pytest  # noqa: E402

from app import create_app  # noqa: E402
from app.database import engine  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.exc import OperationalError  # noqa: E402


@pytest.fixture(scope="module")
def c():
    cliente = create_app().test_client()
    usuario = cliente.post("/api/auth/registro", json={
        "nombre_completo": "Cuenta de pruebas",
        "email": "sesion@pruebas.local",
        "password": "ClaveDePrueba123",
        "rol": "arquitecto",
        "autoriza_datos": True,
    }).get_json()
    with engine.begin() as con:
        con.execute(text("UPDATE USUARIOS SET rol='administrador' WHERE id_usuario=:id"), {"id": usuario["id_usuario"]})
    return cliente


@pytest.fixture(scope="module")
def datos(c):
    u = c.post("/api/usuarios", json={"nombre_completo": "Ana", "email": "ana@ejemplo.com", "rol": "ingeniero"}).get_json()
    p = c.post("/api/proyectos", json={"id_usuario": u["id_usuario"], "nombre_obra": "Casa de prueba"}).get_json()
    ins = {}
    for n, u_, costo in [("Concreto", "m3", 485000), ("Acero", "varilla", 46500), ("Oficial", "jornal", 115000)]:
        ins[n] = c.post("/api/insumos", json={"nombre_insumo": n, "unidad_medida": u_, "costo_unitario": costo}).get_json()
    return {"proyecto": p["id_proyecto"], "insumos": ins}


def test_salud(c):
    assert c.get("/api/salud").get_json() == {"estado": "ok"}


def test_cors_permite_frontend_con_sesion(c):
    response = c.get("/api/salud", headers={"Origin": "http://localhost:5173"})
    assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:5173"
    assert response.headers["Access-Control-Allow-Credentials"] == "true"


def test_origen_no_configurado_no_recibe_cors(c):
    response = c.get("/api/salud", headers={"Origin": "https://sitio-malicioso.example"})
    assert "Access-Control-Allow-Origin" not in response.headers


def test_registro_login_y_cookie_de_sesion(c):
    cliente = create_app().test_client()
    datos = {
        "nombre_completo": "Usuario Auth",
        "email": "usuario.auth@pruebas.local",
        "password": "ClaveSegura123!",
        "rol": "cliente",
        "autoriza_datos": True,
    }
    registro = cliente.post("/api/auth/registro", json=datos)
    assert registro.status_code == 201
    assert registro.get_json()["rol"] == "cliente"
    cookie = registro.headers["Set-Cookie"]
    assert "HttpOnly" in cookie
    assert "SameSite=Lax" in cookie
    assert "Secure" not in cookie  # Vite de desarrollo se sirve por HTTP.
    assert cliente.get("/api/auth/sesion").get_json()["email"] == datos["email"]

    cliente.post("/api/auth/logout")
    acceso = cliente.post("/api/auth/login", json={"email": datos["email"], "password": datos["password"]})
    assert acceso.status_code == 200
    assert acceso.get_json()["email"] == datos["email"]
    assert cliente.get("/api/auth/sesion").status_code == 200


def test_auth_rechaza_datos_invalidos_y_origen_hostil(c):
    cliente = create_app().test_client()
    assert cliente.post("/api/auth/registro", json={
        "nombre_completo": "Hacker", "email": "hacker@pruebas.local",
        "password": "ClaveSegura123!", "rol": "administrador", "autoriza_datos": True,
    }).status_code == 400
    assert cliente.post("/api/auth/login", json={
        "email": "' OR 1=1 --", "password": "incorrecta",
    }).status_code == 401
    rechazado = cliente.post("/api/auth/registro", json={
        "nombre_completo": "Hacker", "email": "hacker@pruebas.local",
        "password": "ClaveSegura123!", "rol": "cliente", "autoriza_datos": True,
    }, headers={"Origin": "https://sitio-malicioso.example"})
    assert rechazado.status_code == 403


def test_respuestas_api_incluyen_cabeceras_de_seguridad(c):
    response = c.get("/api/salud")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Cache-Control"] == "no-store"


def test_sql_no_disponible_responde_json_503(c):
    outage = OperationalError("SELECT 1", {}, RuntimeError("offline"))
    with patch("app.routes.dashboard.engine.connect", side_effect=outage):
        response = c.get("/api/dashboard/resumen")
    assert response.status_code == 503
    assert "error" in response.get_json()


def test_insumo_duplicado_da_409(c, datos):
    r = c.post("/api/insumos", json={"nombre_insumo": "Concreto", "unidad_medida": "m3", "costo_unitario": 1})
    assert r.status_code == 409


def test_validaciones(c, datos):
    assert c.post("/api/insumos", json={"nombre_insumo": "X"}).status_code == 400
    assert c.post("/api/usuarios", json={"nombre_completo": "B", "email": "b@e.co", "rol": "jefe"}).status_code == 400
    assert c.get("/api/presupuestos/99999").status_code == 404
    response = c.post("/api/presupuestos", json={
        "id_proyecto": datos["proyecto"],
        "detalle": [{"id_insumo": datos["insumos"]["Concreto"]["id_insumo"], "cantidad": float("nan")}],
    })
    assert response.status_code == 400


def test_presupuesto_calcula_total(c, datos):
    i = datos["insumos"]
    lineas = [{"id_insumo": i["Concreto"]["id_insumo"], "cantidad": 0.95},
              {"id_insumo": i["Acero"]["id_insumo"], "cantidad": 8},
              {"id_insumo": i["Oficial"]["id_insumo"], "cantidad": 2}]
    p = c.post("/api/presupuestos", json={"id_proyecto": datos["proyecto"], "detalle": lineas}).get_json()
    assert p["costo_total"] == 0.95 * 485000 + 8 * 46500 + 2 * 115000
    assert len(p["detalle"]) == 3
    assert c.post(f"/api/presupuestos/{p['id_presupuesto']}/calcular").get_json()["costo_total"] == p["costo_total"]


def test_duplicar_usa_costos_vigentes(c, datos):
    i = datos["insumos"]["Acero"]
    p = c.post("/api/presupuestos", json={"id_proyecto": datos["proyecto"],
                                           "detalle": [{"id_insumo": i["id_insumo"], "cantidad": 10}]}).get_json()
    c.put(f"/api/insumos/{i['id_insumo']}", json={"nombre_insumo": "Acero", "unidad_medida": "varilla", "costo_unitario": 50000})
    copia = c.post(f"/api/presupuestos/{p['id_presupuesto']}/duplicar").get_json()
    assert p["costo_total"] == 465000       # el original conserva el costo con que se calculó
    assert copia["costo_total"] == 500000   # la copia toma el costo actual del catálogo


def test_insumo_en_uso_no_se_borra(c, datos):
    assert c.delete(f"/api/insumos/{datos['insumos']['Concreto']['id_insumo']}").status_code == 409
