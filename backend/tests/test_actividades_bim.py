"""CRUD documental, autorización y composición SQL + MongoDB."""

from datetime import datetime, timezone

import pytest
from pymongo.errors import ServerSelectionTimeoutError

from app import create_app
from app.errors import ErrorApi
from app.services.actividades_bim import (
    actualizar_actividad_bim,
    crear_actividad_bim,
    eliminar_actividad_bim,
    listar_actividades_bim,
    obtener_actividad_bim,
)


@pytest.fixture
def app_cliente(mongo_store):
    """Crea una sesión autenticada con su identidad en MongoDB."""
    usuario = {
        "id_usuario": 101,
        "nombre_completo": "Arq. Andrés Cepeda",
        "email": "andres@bimetrics.local",
        "rol": "arquitecto",
        "password_hash": "hash-no-usado-en-este-test",
        "fecha_creacion": datetime.now(timezone.utc),
    }
    mongo_store["users"]["usuarios"].insert_one(usuario)
    app = create_app()
    cliente = app.test_client()
    cliente.environ_base["HTTP_ORIGIN"] = "http://localhost:5173"
    with cliente.session_transaction() as sesion:
        sesion["id_usuario"] = 101
    return cliente


def _actividad(id_usuario=101):
    return {
        "id_usuario": id_usuario,
        "tipo_evento": "importacion_revit_txt",
        "software_origen": "Autodesk Revit 2024",
        "nombre_archivo": "Computos_Estructurales.txt",
        "estado": "completado",
        "detalles_bim": {
            "num_elementos": 42,
            "volumen_total_m3": 18.75,
            "advertencias": ["Elemento sin longitud explícita"],
        },
    }


def test_crud_documental_completo(mongo_store):
    creado = crear_actividad_bim(_actividad())
    assert creado["id"]
    assert creado["detalles_bim"]["num_elementos"] == 42

    consultado = obtener_actividad_bim(creado["id"])
    assert consultado["nombre_archivo"] == "Computos_Estructurales.txt"
    assert listar_actividades_bim(id_usuario=101, limite=5)[0]["id"] == creado["id"]

    actualizado = actualizar_actividad_bim(
        creado["id"], {"estado": "advertencia", "detalles_bim": {"revisado": True}},
        id_usuario=101,
    )
    assert actualizado["estado"] == "advertencia"
    assert actualizado["detalles_bim"]["revisado"] is True
    assert eliminar_actividad_bim(creado["id"], id_usuario=101) is True
    assert obtener_actividad_bim(creado["id"]) is None


def test_actualizacion_rechaza_campos_no_permitidos(mongo_store):
    creado = crear_actividad_bim(_actividad())
    with pytest.raises(ErrorApi, match="campos modificables"):
        actualizar_actividad_bim(creado["id"], {"id_usuario": 999})


def test_endpoint_dashboard_combina_sql_y_mongodb(app_cliente, mongo_store):
    proyecto = app_cliente.post("/api/proyectos", json={"nombre_obra": "Casa BIM"})
    assert proyecto.status_code == 201
    crear_actividad_bim({
        **_actividad(),
        "tipo_evento": "importacion_archicad_txt",
        "software_origen": "Graphisoft Archicad 27",
        "nombre_archivo": "Muros_Planta1.txt",
    })

    respuesta = app_cliente.get("/api/dashboard/resumen")
    assert respuesta.status_code == 200
    datos = respuesta.get_json()
    assert datos["usuario"]["nombre_completo"] == "Arq. Andrés Cepeda"
    assert datos["resumen"]["total_proyectos"] == 1
    assert datos["resumen"]["ultima_actividad_bim"]["software_origen"] == "Graphisoft Archicad 27"
    assert datos["resumen"]["mongodb_disponible"] is True


def test_endpoint_perfil_y_actividad_son_propios(app_cliente, mongo_store):
    crear_actividad_bim(_actividad())
    respuesta = app_cliente.get("/api/actividades-bim/usuario/101")
    assert respuesta.status_code == 200
    datos = respuesta.get_json()
    assert datos["usuario"]["email"] == "andres@bimetrics.local"
    assert datos["actividades_recientes"][0]["nombre_archivo"] == "Computos_Estructurales.txt"


def test_usuario_ajeno_no_es_visible(app_cliente):
    respuesta = app_cliente.get("/api/actividades-bim/usuario/999999")
    assert respuesta.status_code == 404


def test_obra_de_otra_persona_no_se_asocia(app_cliente, mongo_store):
    otra = mongo_store["users"]["usuarios"]
    otra.insert_one({
        "id_usuario": 202, "nombre_completo": "Otra persona", "email": "otra@example.test",
        "rol": "arquitecto", "password_hash": "hash",
    })
    proyecto = app_cliente.post("/api/proyectos", json={"nombre_obra": "Obra propia"}).get_json()
    # La referencia enviada tiene que ser una obra SQL existente y accesible.
    respuesta = app_cliente.post("/api/actividades-bim", json={
        **_actividad(), "id_proyecto": proyecto["id_proyecto"] + 1,
    })
    assert respuesta.status_code == 404


def test_limite_bim_invalido_devuelve_400(app_cliente):
    respuesta = app_cliente.get("/api/actividades-bim/usuario/101?limite=abc")
    assert respuesta.status_code == 400


def test_mongo_no_disponible_responde_503(app_cliente, monkeypatch):
    monkeypatch.setattr(
        "app.routes.actividades_bim.listar_actividades_bim",
        lambda **_kwargs: (_ for _ in ()).throw(ServerSelectionTimeoutError("offline")),
    )
    respuesta = app_cliente.get("/api/actividades-bim/usuario/101")
    assert respuesta.status_code == 503


def test_registro_rechaza_estado_invalido(mongo_store):
    with pytest.raises(ErrorApi, match="estado"):
        crear_actividad_bim({**_actividad(), "estado": {"$ne": "fallido"}})


def test_id_no_es_un_objectid_valido():
    with pytest.raises(ErrorApi, match="ObjectId"):
        obtener_actividad_bim("no-es-un-id")
