"""Casos de uso transaccionales de presupuestos."""

from datetime import date

from sqlalchemy import text

from ..database import operational_engine
from ..errors import ErrorApi
from ..utils import filas
from .presupuestos import agregar_linea, presupuesto_completo, recalcular


def _exigir_proyecto_accesible(connection, id_proyecto, id_usuario):
    consulta = text(
        "SELECT id_proyecto FROM PROYECTOS p WHERE p.id_proyecto=:proyecto AND "
        "(p.id_usuario=:usuario OR EXISTS (SELECT 1 FROM PROYECTO_COLABORADORES c "
        "WHERE c.id_proyecto=p.id_proyecto AND c.id_usuario=:usuario))"
    )
    existe = connection.execute(consulta, {"proyecto": id_proyecto, "usuario": id_usuario}).first()
    if not existe:
        raise ErrorApi(404, "El proyecto no existe")


def _obtener_presupuesto_accesible(connection, id_presupuesto, id_usuario):
    consulta = text(
        "SELECT p.id_presupuesto, p.id_proyecto FROM PRESUPUESTOS p "
        "JOIN PROYECTOS y ON y.id_proyecto=p.id_proyecto WHERE p.id_presupuesto=:presupuesto AND "
        "(y.id_usuario=:usuario OR EXISTS (SELECT 1 FROM PROYECTO_COLABORADORES c "
        "WHERE c.id_proyecto=y.id_proyecto AND c.id_usuario=:usuario))"
    )
    presupuesto = connection.execute(
        consulta, {"presupuesto": id_presupuesto, "usuario": id_usuario}
    ).mappings().first()
    if not presupuesto:
        raise ErrorApi(404, "El presupuesto no existe")
    return presupuesto


def _crear_cabecera(connection, id_proyecto):
    resultado = connection.execute(
        text("INSERT INTO PRESUPUESTOS (id_proyecto, fecha_calculo, costo_total) "
             "VALUES (:proyecto, :fecha, 0)"),
        {"proyecto": id_proyecto, "fecha": date.today().isoformat()},
    )
    return resultado.lastrowid


def listar_presupuestos(id_usuario, id_proyecto=None):
    """Lista presupuestos propios y compartidos, opcionalmente por proyecto."""
    consulta = (
        "SELECT p.*, y.nombre_obra, y.ciudad FROM PRESUPUESTOS p "
        "JOIN PROYECTOS y ON y.id_proyecto=p.id_proyecto WHERE "
        "(y.id_usuario=:usuario OR EXISTS (SELECT 1 FROM PROYECTO_COLABORADORES c "
        "WHERE c.id_proyecto=y.id_proyecto AND c.id_usuario=:usuario))"
    )
    parametros = {"usuario": id_usuario}
    if id_proyecto is not None:
        consulta += " AND p.id_proyecto=:proyecto"
        parametros["proyecto"] = id_proyecto
    consulta += " ORDER BY p.fecha_calculo DESC, p.id_presupuesto DESC"
    with operational_engine.connect() as connection:
        return filas(connection.execute(text(consulta), parametros))


def obtener_presupuesto(id_presupuesto, id_usuario):
    """Devuelve el presupuesto completo tras comprobar permisos."""
    with operational_engine.connect() as connection:
        _obtener_presupuesto_accesible(connection, id_presupuesto, id_usuario)
        return presupuesto_completo(connection, id_presupuesto)


def crear_presupuesto(id_usuario, id_proyecto, lineas):
    """Crea presupuesto y agrega sus líneas en una sola transacción."""
    with operational_engine.begin() as connection:
        _exigir_proyecto_accesible(connection, id_proyecto, id_usuario)
        id_presupuesto = _crear_cabecera(connection, id_proyecto)
        ciudad = connection.execute(
            text("SELECT ciudad FROM PROYECTOS WHERE id_proyecto=:proyecto"), {"proyecto": id_proyecto}
        ).scalar()
        for linea in lineas:
            agregar_linea(connection, id_presupuesto, linea.get("id_insumo"), linea.get("cantidad"), ciudad)
        recalcular(connection, id_presupuesto)
        return presupuesto_completo(connection, id_presupuesto)


def agregar_linea_presupuesto(id_presupuesto, id_usuario, id_insumo, cantidad, lineas_mano_obra=None):
    """Agrega el insumo y su mano de obra sugerida en una sola transacción."""
    lineas_mano_obra = lineas_mano_obra or []
    with operational_engine.begin() as connection:
        presupuesto = _obtener_presupuesto_accesible(connection, id_presupuesto, id_usuario)
        ciudad = connection.execute(
            text("SELECT ciudad FROM PROYECTOS WHERE id_proyecto=:proyecto"),
            {"proyecto": presupuesto["id_proyecto"]},
        ).scalar()
        agregar_linea(connection, id_presupuesto, id_insumo, cantidad, ciudad)
        for linea in lineas_mano_obra:
            agregar_linea(
                connection,
                id_presupuesto,
                linea["id_insumo"],
                linea["cantidad"],
                ciudad,
            )
        recalcular(connection, id_presupuesto)
        return presupuesto_completo(connection, id_presupuesto)


def quitar_linea_presupuesto(id_presupuesto, id_detalle, id_usuario):
    """Elimina una línea existente y actualiza el costo total."""
    with operational_engine.begin() as connection:
        _obtener_presupuesto_accesible(connection, id_presupuesto, id_usuario)
        resultado = connection.execute(
            text("DELETE FROM DETALLE_PRESUPUESTO WHERE id_detalle=:detalle AND id_presupuesto=:presupuesto"),
            {"detalle": id_detalle, "presupuesto": id_presupuesto},
        )
        if resultado.rowcount == 0:
            raise ErrorApi(404, f"El presupuesto {id_presupuesto} no tiene la línea {id_detalle}")
        recalcular(connection, id_presupuesto)
        return presupuesto_completo(connection, id_presupuesto)


def calcular_presupuesto(id_presupuesto, id_usuario):
    """Recalcula y devuelve el costo total del presupuesto."""
    with operational_engine.begin() as connection:
        _obtener_presupuesto_accesible(connection, id_presupuesto, id_usuario)
        return recalcular(connection, id_presupuesto)


def duplicar_presupuesto(id_presupuesto, id_usuario, id_proyecto_destino=None):
    """Duplica líneas y aplica los precios vigentes del catálogo de destino."""
    with operational_engine.begin() as connection:
        original = _obtener_presupuesto_accesible(connection, id_presupuesto, id_usuario)
        destino = original["id_proyecto"] if id_proyecto_destino is None else id_proyecto_destino
        _exigir_proyecto_accesible(connection, destino, id_usuario)
        id_nuevo = _crear_cabecera(connection, destino)
        connection.execute(
            text(
                "INSERT INTO DETALLE_PRESUPUESTO "
                "(id_presupuesto, id_insumo, cantidad, costo_unitario_aplicado) "
                "SELECT :nuevo, d.id_insumo, d.cantidad, "
                "COALESCE(pc.costo_unitario, NULLIF(i.costo_unitario, 0), d.costo_unitario_aplicado) "
                "FROM DETALLE_PRESUPUESTO d JOIN INSUMOS i ON i.id_insumo=d.id_insumo "
                "JOIN PROYECTOS y ON y.id_proyecto=:destino "
                "LEFT JOIN PRECIOS_CIUDAD pc ON pc.id_insumo=i.id_insumo AND pc.ciudad=y.ciudad "
                "WHERE d.id_presupuesto=:original"
            ),
            {"nuevo": id_nuevo, "original": id_presupuesto, "destino": destino},
        )
        recalcular(connection, id_nuevo)
        return presupuesto_completo(connection, id_nuevo)
