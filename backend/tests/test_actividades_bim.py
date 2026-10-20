"""Pruebas unitarias y de integración para la persistencia políglota y actividades BIM NoSQL."""
import os
import tempfile
from unittest.mock import patch

# Fijar base de pruebas SQLite temporal antes de cargar la app
os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/prueba_poliglota.db"
os.environ["SECRET_KEY"] = "clave-super-secreta-para-tests-poliglotas-12345"

import mongomock
import pytest
from pymongo.errors import ServerSelectionTimeoutError
from sqlalchemy import text

from app import create_app
from app.database import engine
from app.services.actividades_bim import (
    actualizar_actividad_bim,
    crear_actividad_bim,
    eliminar_actividad_bim,
    listar_actividades_bim,
    obtener_actividad_bim,
)


@pytest.fixture(scope="module")
def mock_db():
    """Mock de MongoDB en memoria para pruebas rápidas y determinísticas."""
    cliente_mock = mongomock.MongoClient()
    db_mock = cliente_mock["bimetrics_test_nosql"]
    with patch("app.services.actividades_bim.get_mongo_db", return_value=db_mock), \
         patch("app.database.get_mongo_db", return_value=db_mock):
        yield db_mock


@pytest.fixture(scope="module")
def app_cliente(mock_db):
    """Cliente de pruebas de Flask con base de datos SQL y NoSQL mockeada."""
    app = create_app()
    with app.test_client() as cliente:
        with cliente.session_transaction() as sesion:
            sesion["id_usuario"] = 101
        # Insertar un usuario directo en SQL para las pruebas
        with engine.begin() as con:
            con.execute(text("""
                INSERT INTO USUARIOS (id_usuario, nombre_completo, email, rol)
                VALUES (101, 'Arq. Andrés Cepeda', 'andres@bimetrics.local', 'arquitecto')
            """))
        yield cliente


def test_crud_servicio_nosql(mock_db):
    """Prueba el ciclo de vida completo de un documento en MongoDB."""
    # 1. Crear documento
    payload = {
        "id_usuario": 101,
        "tipo_evento": "importacion_revit_txt",
        "software_origen": "Autodesk Revit 2024",
        "nombre_archivo": "Computos_Estructural_Vigas.txt",
        "estado": "completado",
        "detalles_bim": {
            "num_elementos": 42,
            "volumen_total_m3": 18.75,
            "advertencias": ["Línea 12: acero 3/8 sin longitud explícita"]
        }
    }
    creado = crear_actividad_bim(payload)
    assert creado["id"] is not None
    assert creado["tipo_evento"] == "importacion_revit_txt"
    assert creado["detalles_bim"]["num_elementos"] == 42
    id_actividad = creado["id"]

    # 2. Consultar por ID
    consultado = obtener_actividad_bim(id_actividad)
    assert consultado is not None
    assert consultado["nombre_archivo"] == "Computos_Estructural_Vigas.txt"

    # 3. Listar por usuario
    lista = listar_actividades_bim(id_usuario=101, limite=5)
    assert len(lista) >= 1
    assert lista[0]["id"] == id_actividad

    # 4. Actualizar
    actualizado = actualizar_actividad_bim(id_actividad, {"estado": "advertencia", "detalles_bim": {"revisado": True}})
    assert actualizado["estado"] == "advertencia"
    assert actualizado["detalles_bim"]["revisado"] is True

    # 5. Eliminar
    eliminado = eliminar_actividad_bim(id_actividad)
    assert eliminado is True
    assert obtener_actividad_bim(id_actividad) is None


def test_endpoint_poliglota_exitoso(app_cliente, mock_db):
    """Verifica que el endpoint híbrido consulte SQL (usuario) + NoSQL (logs BIM)."""
    # Insertar actividad en NoSQL para el usuario 101
    crear_actividad_bim({
        "id_usuario": 101,
        "tipo_evento": "importacion_archicad_txt",
        "software_origen": "Graphisoft ArchiCAD 27",
        "nombre_archivo": "Muros_Planta1.txt",
        "estado": "completado",
        "detalles_bim": {"muros_contados": 15}
    })

    # Consultar endpoint híbrido
    resp = app_cliente.get("/api/actividades-bim/usuario/101")
    assert resp.status_code == 200
    data = resp.get_json()

    # Validar sección SQL
    assert "usuario" in data
    assert data["usuario"]["id_usuario"] == 101
    assert data["usuario"]["nombre_completo"] == "Arq. Andrés Cepeda"
    assert data["usuario"]["rol"] == "arquitecto"

    # Validar sección NoSQL y resumen
    assert "resumen_bim" in data
    assert data["resumen_bim"]["total_actividades_recientes"] >= 1
    assert data["resumen_bim"]["software_mas_frecuente"] == "Graphisoft ArchiCAD 27"

    assert "actividades_recientes" in data
    assert len(data["actividades_recientes"]) >= 1
    assert data["actividades_recientes"][0]["nombre_archivo"] == "Muros_Planta1.txt"


def test_endpoint_poliglota_usuario_no_existe(app_cliente, mock_db):
    """Si el usuario no existe en la base relacional SQL, debe retornar 404."""
    resp = app_cliente.get("/api/actividades-bim/usuario/999999")
    assert resp.status_code == 404
    assert "no existe usuario" in resp.get_json()["error"].lower()


def test_limite_bim_invalido_devuelve_400(app_cliente):
    resp = app_cliente.get("/api/actividades-bim/usuario/101?limite=abc")
    assert resp.status_code == 400
    assert "entero" in resp.get_json()["error"].lower()


def test_mongo_no_disponible_responde_json_503(app_cliente):
    with patch("app.routes.actividades_bim.listar_actividades_bim", side_effect=ServerSelectionTimeoutError("offline")):
        resp = app_cliente.get("/api/actividades-bim/usuario/101")
    assert resp.status_code == 503
    assert "error" in resp.get_json()


def test_validacion_integridad_cruzada_al_crear(app_cliente, mock_db):
    """No permite registrar una actividad BIM si el usuario no existe en SQL."""
    with engine.begin() as con:
        con.execute(text("UPDATE USUARIOS SET rol='administrador' WHERE id_usuario=101"))
    resp = app_cliente.post("/api/actividades-bim", json={
        "id_usuario": 88888,  # Usuario inexistente
        "tipo_evento": "importacion_revit_txt",
        "software_origen": "Revit 2024",
        "nombre_archivo": "Prueba.txt"
    })
    assert resp.status_code == 404
    assert "no existe en sql" in resp.get_json()["error"].lower()
    with engine.begin() as con:
        con.execute(text("UPDATE USUARIOS SET rol='arquitecto' WHERE id_usuario=101"))
