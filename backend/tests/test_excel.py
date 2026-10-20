"""Pruebas unitarias para la exportación de presupuestos a Excel (.xlsx)."""
import io
import os
import tempfile
import openpyxl
import pytest
from sqlalchemy import text

os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/prueba_excel.db"
os.environ["SECRET_KEY"] = "clave-super-secreta-para-tests-excel-12345"

from app import create_app
from app.database import engine
from app.services.excel import exportar_presupuesto_excel


def test_generacion_servicio_excel():
    """Valida la estructura, fórmulas y estilos de la hoja de cálculo generada por openpyxl."""
    mock_presupuesto = {
        "id_presupuesto": 1,
        "nombre_obra": "Edificio Residencial Las Palmas",
        "ciudad": "Bogotá",
        "fecha_calculo": "2026-10-19",
        "costo_total": 1611150.0,
        "detalle": [
            {
                "id_detalle": 10,
                "nombre_insumo": "Concreto 3000 PSI",
                "unidad_medida": "m3",
                "cantidad": 0.95,
                "costo_unitario_aplicado": 485000.0,
                "subtotal": 460750.0,
            },
            {
                "id_detalle": 11,
                "nombre_insumo": "Acero de refuerzo 1/2 pulg",
                "unidad_medida": "varilla",
                "cantidad": 8.0,
                "costo_unitario_aplicado": 46500.0,
                "subtotal": 372000.0,
            }
        ]
    }

    stream = exportar_presupuesto_excel(mock_presupuesto)
    assert isinstance(stream, io.BytesIO)
    bytes_data = stream.getvalue()
    assert len(bytes_data) > 2000

    # Cargar y verificar con openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(bytes_data))
    assert "Presupuesto de Obra" in wb.sheetnames
    ws = wb["Presupuesto de Obra"]

    # Verificar título y metadatos
    assert "BIMETRICS" in str(ws["A1"].value)
    assert ws["B3"].value == "Edificio Residencial Las Palmas"
    assert ws["F3"].value == "Bogotá"

    # Verificar encabezados
    assert ws["B6"].value == "DESCRIPCIÓN DEL INSUMO"
    assert ws["E6"].value == "PRECIO UNITARIO"
    assert ws["F6"].value == "SUBTOTAL"

    # Verificar datos de las partidas
    assert ws["B7"].value == "Concreto 3000 PSI"
    assert ws["C7"].value == "m3"
    assert ws["D7"].value == 0.95
    assert ws["E7"].value == 485000.0
    assert ws["F7"].value == "=D7*E7"

    # Verificar segunda partida
    assert ws["B8"].value == "Acero de refuerzo 1/2 pulg"
    assert ws["F8"].value == "=D8*E8"

    # Fila de total con fórmula SUM
    assert ws["A9"].value == "TOTAL PRESUPUESTADO (COP):"
    assert ws["F9"].value == "=SUM(F7:F8)"


def test_endpoint_excel_presupuesto():
    """Valida el endpoint HTTP GET /api/presupuestos/<id>/excel."""
    app = create_app()
    with app.test_client() as cliente:
        # 1. Registrar usuario y autenticar
        with cliente.session_transaction() as sess:
            sess["id_usuario"] = 555

        with engine.begin() as con:
            con.execute(text("""
                INSERT INTO USUARIOS (id_usuario, nombre_completo, email, rol)
                VALUES (555, 'Ing. Carlos Mendoza', 'carlos@bimetrics.local', 'ingeniero')
            """))
            con.execute(text("""
                INSERT INTO PROYECTOS (id_proyecto, id_usuario, nombre_obra, ciudad)
                VALUES (777, 555, 'Torre Horizonte', 'Medellín')
            """))
            con.execute(text("""
                INSERT INTO PRESUPUESTOS (id_presupuesto, id_proyecto, fecha_calculo, costo_total)
                VALUES (888, 777, '2026-10-19', 485000)
            """))
            con.execute(text("""
                INSERT INTO INSUMOS (id_insumo, nombre_insumo, unidad_medida, costo_unitario)
                VALUES (999, 'Mortero 1:3', 'm3', 380000)
            """))
            con.execute(text("""
                INSERT INTO DETALLE_PRESUPUESTO (id_presupuesto, id_insumo, cantidad, costo_unitario_aplicado)
                VALUES (888, 999, 1.5, 380000)
            """))

        # 2. Descargar Excel mediante el endpoint
        resp = cliente.get("/api/presupuestos/888/excel")
        assert resp.status_code == 200
        assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in resp.headers.get("Content-Type", "")
        assert "attachment" in resp.headers.get("Content-Disposition", "")
        assert "Presupuesto_Torre_Horizonte_888.xlsx" in resp.headers.get("Content-Disposition", "")
        assert len(resp.data) > 2000
