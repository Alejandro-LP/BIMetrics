"""Pruebas de la API. Ejecutar desde backend/:  python -m pytest -q"""
import os
import tempfile

# La base de pruebas va en una carpeta temporal, nunca en data/
os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/prueba.db"

import pytest  # noqa: E402

from app import create_app  # noqa: E402


@pytest.fixture(scope="module")
def c():
    cliente = create_app().test_client()
    cliente.post("/api/auth/registro", json={
        "nombre_completo": "Cuenta de pruebas",
        "email": "sesion@pruebas.local",
        "password": "ClaveDePrueba123",
        "rol": "arquitecto",
    })
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


def test_insumo_duplicado_da_409(c, datos):
    r = c.post("/api/insumos", json={"nombre_insumo": "Concreto", "unidad_medida": "m3", "costo_unitario": 1})
    assert r.status_code == 409


def test_validaciones(c, datos):
    assert c.post("/api/insumos", json={"nombre_insumo": "X"}).status_code == 400
    assert c.post("/api/usuarios", json={"nombre_completo": "B", "email": "b@e.co", "rol": "jefe"}).status_code == 400
    assert c.get("/api/presupuestos/99999").status_code == 404


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
