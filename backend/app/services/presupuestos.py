"""Lógica de negocio de presupuestos (cálculo paramétrico)."""
from sqlalchemy import text

from ..errors import ErrorApi
from ..utils import filas, limpiar, numero, una


def recalcular(con, id_pres):
    """Suma cantidad x costo aplicado de cada línea y guarda el costo_total."""
    con.execute(text(
        "UPDATE PRESUPUESTOS SET costo_total = (SELECT COALESCE(ROUND(SUM(cantidad * costo_unitario_aplicado), 2), 0) "
        "FROM DETALLE_PRESUPUESTO WHERE id_presupuesto = :p) WHERE id_presupuesto = :p"), {"p": id_pres})
    return limpiar(con.execute(text(
        "SELECT costo_total FROM PRESUPUESTOS WHERE id_presupuesto = :p"), {"p": id_pres}).scalar())


def agregar_linea(con, id_pres, id_insumo, cantidad, ciudad=None):
    """Agrega un insumo copiando su costo vigente del catálogo."""
    cant = numero(cantidad, "cantidad", 0, estricto=True)
    precio = con.execute(text(
        "SELECT COALESCE(pc.costo_unitario, i.costo_unitario) FROM INSUMOS i "
        "LEFT JOIN PRECIOS_CIUDAD pc ON pc.id_insumo=i.id_insumo AND pc.ciudad=:ciudad "
        "WHERE i.id_insumo=:i"), {"i": id_insumo, "ciudad": ciudad or ""}).scalar()
    if precio is None:
        raise ErrorApi(400, f"El insumo {id_insumo} no existe")
    if float(precio) <= 0:
        raise ErrorApi(400, f"No hay un precio de referencia registrado para este insumo en {ciudad or 'la ciudad del proyecto'}")
    con.execute(text(
        "INSERT INTO DETALLE_PRESUPUESTO (id_presupuesto, id_insumo, cantidad, costo_unitario_aplicado) "
        "VALUES (:p, :i, :c, :precio)"),
        {"p": id_pres, "i": id_insumo, "c": cant, "precio": precio})


def presupuesto_completo(con, id_pres):
    p = una(con.execute(text(
        "SELECT p.*, y.nombre_obra, y.ciudad FROM PRESUPUESTOS p "
        "JOIN PROYECTOS y ON y.id_proyecto = p.id_proyecto WHERE p.id_presupuesto = :p"), {"p": id_pres}))
    if p is None:
        raise ErrorApi(404, f"No existe presupuesto con id {id_pres}")
    p["detalle"] = filas(con.execute(text(
        "SELECT d.id_detalle, d.id_insumo, i.nombre_insumo, i.unidad_medida, d.cantidad, "
        "d.costo_unitario_aplicado, ROUND(d.cantidad * d.costo_unitario_aplicado, 2) AS subtotal "
        "FROM DETALLE_PRESUPUESTO d JOIN INSUMOS i ON i.id_insumo = d.id_insumo "
        "WHERE d.id_presupuesto = :p ORDER BY d.id_detalle"), {"p": id_pres}))
    return p
