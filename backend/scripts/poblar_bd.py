"""Carga un único proyecto y presupuesto para demostración.

Uso desde backend/: python -m scripts.poblar_bd --reset
Los datos son ilustrativos y no representan una cotización oficial.
"""
import argparse
import os

from sqlalchemy import inspect, text

from app.database import engine
from app.models import TABLAS, meta


INSUMOS = [
    ("Concreto premezclado 3000 PSI", "m³", 485000, 0.95),
    ("Acero corrugado 1/2\"", "varilla", 46500, 8),
    ("Acero corrugado 3/8\"", "varilla", 30000, 10),
    ("Alambre negro calibre 18", "kg", 7800, 3),
    ("Oficial de construcción", "jornal", 115000, 2),
    ("Ayudante de obra", "jornal", 75000, 3),
]


def main(reset: bool):
    meta.create_all(engine)
    if "ciudad" not in {column["name"] for column in inspect(engine).get_columns("PROYECTOS")}:
        with engine.begin() as con:
            con.execute(text("ALTER TABLE PROYECTOS ADD COLUMN ciudad VARCHAR(100)"))
    with engine.begin() as con:
        if reset:
            for tabla in reversed(TABLAS):
                con.execute(text(f"DELETE FROM {tabla}"))
        elif con.execute(text("SELECT COUNT(*) FROM PROYECTOS")).scalar():
            print("Ya existen datos. Usa --reset para reemplazarlos por la demo única.")
            return

        usuario = con.execute(text(
            "INSERT INTO USUARIOS (nombre_completo, email, rol) "
            "VALUES (:nombre, :email, :rol)"),
            {"nombre": "Equipo de demostración", "email": "demo@bimetrics.local", "rol": "arquitecto"})
        proyecto = con.execute(text(
            "INSERT INTO PROYECTOS (id_usuario, nombre_obra, cliente, ciudad) "
            "VALUES (:usuario, :obra, :cliente, :ciudad)"),
            {"usuario": usuario.lastrowid, "obra": "Viga entre zapatas · 10 m", "cliente": "Proyecto de demostración", "ciudad": "Bogotá"})
        presupuesto = con.execute(text(
            "INSERT INTO PRESUPUESTOS (id_proyecto, fecha_calculo, costo_total) "
            "VALUES (:proyecto, CURRENT_DATE, 0)"), {"proyecto": proyecto.lastrowid})

        total = 0
        for nombre, unidad, precio, cantidad in INSUMOS:
            insumo = con.execute(text(
                "INSERT INTO INSUMOS (nombre_insumo, unidad_medida, costo_unitario) "
                "VALUES (:nombre, :unidad, :precio)"),
                {"nombre": nombre, "unidad": unidad, "precio": precio})
            con.execute(text(
                "INSERT INTO PRECIOS_CIUDAD (id_insumo, ciudad, costo_unitario) "
                "VALUES (:insumo, :ciudad, :precio)"),
                {"insumo": insumo.lastrowid, "ciudad": "Bogotá", "precio": precio})
            subtotal = cantidad * precio
            total += subtotal
            con.execute(text(
                "INSERT INTO DETALLE_PRESUPUESTO "
                "(id_presupuesto, id_insumo, cantidad, costo_unitario_aplicado) "
                "VALUES (:presupuesto, :insumo, :cantidad, :precio)"),
                {"presupuesto": presupuesto.lastrowid, "insumo": insumo.lastrowid,
                 "cantidad": cantidad, "precio": precio})
        con.execute(text("UPDATE PRESUPUESTOS SET costo_total = :total WHERE id_presupuesto = :id"),
                    {"total": total, "id": presupuesto.lastrowid})

    with engine.connect() as con:
        conteo = {tabla: con.execute(text(f"SELECT COUNT(*) FROM {tabla}")).scalar() for tabla in TABLAS}
    destino = os.path.abspath(engine.url.database) if engine.url.get_backend_name() == "sqlite" \
        else engine.url.render_as_string(hide_password=True)
    print(f"Demo única creada: viga entre zapatas · total ${total:,.0f} COP.")
    print("Registros:", ", ".join(f"{tabla}: {cantidad}" for tabla, cantidad in conteo.items()))
    print("Ubicación:", destino)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Carga la demo única de BIMetrics")
    parser.add_argument("--reset", action="store_true", help="borra los datos existentes y carga solo la demo")
    main(parser.parse_args().reset)
