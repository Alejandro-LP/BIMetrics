"""Lógica de negocio de presupuestos (cálculo paramétrico)."""
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import text

from ..errors import ErrorApi
from ..utils import filas, limpiar, numero, una


def _dinero(valor):
    """Redondea importes de forma decimal (mitad hacia arriba) a centavos."""
    return Decimal(str(valor or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def recalcular(con, id_pres):
    """Calcula costo directo más AIU porcentual aplicado sobre el costo directo."""
    presupuesto = con.execute(text(
        "SELECT porcentaje_administracion, porcentaje_imprevistos, porcentaje_utilidad "
        "FROM PRESUPUESTOS WHERE id_presupuesto=:p"), {"p": id_pres}).mappings().first()
    if not presupuesto:
        raise ErrorApi(404, f"No existe presupuesto con id {id_pres}")
    directo = _dinero(con.execute(text(
        "SELECT COALESCE(SUM(ROUND(cantidad * costo_unitario_aplicado, 2)), 0) "
        "FROM DETALLE_PRESUPUESTO WHERE id_presupuesto=:p"), {"p": id_pres}).scalar() or 0)
    valores_aiu = sum((_dinero(directo * Decimal(str(presupuesto[campo] or 0)) / 100) for campo in (
        "porcentaje_administracion", "porcentaje_imprevistos", "porcentaje_utilidad"
    )), Decimal("0.00"))
    total = _dinero(directo + valores_aiu)
    con.execute(text("UPDATE PRESUPUESTOS SET costo_total=:total WHERE id_presupuesto=:p"),
                {"total": str(total), "p": id_pres})
    return limpiar(total)


def agregar_linea(con, id_pres, id_insumo, cantidad, ciudad=None, capitulo=None):
    """Agrega un insumo copiando su costo vigente del catálogo."""
    cant = numero(cantidad, "cantidad", 0, estricto=True)
    precio = con.execute(text(
        "SELECT COALESCE(pc.costo_unitario, i.costo_unitario), COALESCE(i.activo, 1) FROM INSUMOS i "
        "LEFT JOIN PRECIOS_CIUDAD pc ON pc.id_insumo=i.id_insumo AND pc.ciudad=:ciudad "
        "WHERE i.id_insumo=:i"), {"i": id_insumo, "ciudad": ciudad or ""}).first()
    if not precio:
        raise ErrorApi(400, f"El insumo {id_insumo} no existe")
    if not precio[1]:
        raise ErrorApi(400, f"El insumo {id_insumo} está inactivo y no se puede agregar a un presupuesto")
    precio = precio[0]
    if float(precio) <= 0:
        raise ErrorApi(400, f"No hay un precio de referencia registrado para este insumo en {ciudad or 'la ciudad del proyecto'}")
    con.execute(text(
        "INSERT INTO DETALLE_PRESUPUESTO (id_presupuesto, id_insumo, cantidad, costo_unitario_aplicado, capitulo) "
        "VALUES (:p, :i, :c, :precio, :capitulo)"),
        {"p": id_pres, "i": id_insumo, "c": cant, "precio": precio,
         "capitulo": (capitulo.strip()[:100] if isinstance(capitulo, str) and capitulo.strip() else None)})


def presupuesto_completo(con, id_pres):
    p = una(con.execute(text(
        "SELECT p.*, y.nombre_obra, y.ciudad FROM PRESUPUESTOS p "
        "JOIN PROYECTOS y ON y.id_proyecto = p.id_proyecto WHERE p.id_presupuesto = :p"), {"p": id_pres}))
    if p is None:
        raise ErrorApi(404, f"No existe presupuesto con id {id_pres}")
    p["detalle"] = filas(con.execute(text(
        "SELECT d.id_detalle, d.id_insumo, d.capitulo, "
        "COALESCE(i.nombre_insumo, 'Insumo #' || d.id_insumo) AS nombre_insumo, "
        "COALESCE(i.unidad_medida, 'Ud') AS unidad_medida, d.cantidad, "
        "d.costo_unitario_aplicado, ROUND(d.cantidad * d.costo_unitario_aplicado, 2) AS subtotal "
        "FROM DETALLE_PRESUPUESTO d LEFT JOIN INSUMOS i ON i.id_insumo = d.id_insumo "
        "WHERE d.id_presupuesto = :p ORDER BY COALESCE(d.capitulo, ''), d.id_detalle"), {"p": id_pres}))
    p["costo_directo"] = float(_dinero(sum((Decimal(str(linea.get("subtotal") or 0)) for linea in p["detalle"]), Decimal("0.00"))))
    for etiqueta, columna in (("administracion", "porcentaje_administracion"),
                              ("imprevistos", "porcentaje_imprevistos"),
                              ("utilidad", "porcentaje_utilidad")):
        p[f"valor_{etiqueta}"] = float(_dinero(Decimal(str(p["costo_directo"])) * Decimal(str(p.get(columna) or 0)) / 100))
    return p
