"""Casos de uso transaccionales de presupuestos."""

from datetime import date

from sqlalchemy import select, text
from sqlalchemy.orm import selectinload

from ..database import operational_engine
from ..errors import ErrorApi
from ..catalog_models import Partida, VariacionOpcion
from ..extensions import db
from ..utils import filas
from .presupuestos import agregar_linea, presupuesto_completo, recalcular

MANO_OBRA_ASOCIADA = {
    "0XA110": "0XA130",
    "0XA113": "0XA133",
    "0XA114": "0XA134",
    "0XA115": "0XA135",
    "0XT110": "0XT130",
}


def _crear_o_buscar_insumo_de_partida(connection, partida, ciudad, variacion=None):
    """Crea un insumo operacional a precio de catálogo, nunca a precio del cliente."""
    etiqueta = " · ".join(
        texto for texto in (
            variacion.opcion if variacion else None,
            variacion.parametro if variacion else None,
            variacion.valor_probado if variacion else None,
        ) if texto
    ) if variacion else ""
    prefijo = f"{partida.codigo} · "
    sufijo = f" · {etiqueta}" if etiqueta else ""
    nombre = f"{prefijo}{partida.descripcion[:max(0, 150 - len(prefijo) - len(sufijo))]}{sufijo}"
    precio_catalogo = variacion.precio if variacion and variacion.precio is not None else partida.precio_defecto
    if precio_catalogo is None or float(precio_catalogo) <= 0:
        raise ErrorApi(400, f"La partida {partida.codigo} no tiene un precio positivo en el catálogo SQL")

    id_insumo = connection.execute(
        text("SELECT id_insumo FROM INSUMOS WHERE nombre_insumo=:nombre"), {"nombre": nombre}
    ).scalar()
    if id_insumo is None:
        creado = connection.execute(
            text("INSERT INTO INSUMOS (nombre_insumo, unidad_medida, costo_unitario) VALUES (:n, :u, 0)"),
            {"n": nombre, "u": partida.unidad},
        )
        id_insumo = creado.lastrowid

    id_precio = connection.execute(
        text("SELECT id_precio FROM PRECIOS_CIUDAD WHERE id_insumo=:id AND ciudad=:ciudad"),
        {"id": id_insumo, "ciudad": ciudad},
    ).scalar()
    if id_precio is None:
        connection.execute(
            text("INSERT INTO PRECIOS_CIUDAD (id_insumo, ciudad, costo_unitario) VALUES (:id, :ciudad, :precio)"),
            {"id": id_insumo, "ciudad": ciudad, "precio": precio_catalogo},
        )
    return id_insumo


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
        "SELECT p.* FROM PRESUPUESTOS p "
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


def _crear_cabecera(connection, id_proyecto, aiu=None):
    aiu = aiu or {}
    resultado = connection.execute(
        text("INSERT INTO PRESUPUESTOS (id_proyecto, fecha_calculo, costo_total, "
             "porcentaje_administracion, porcentaje_imprevistos, porcentaje_utilidad) "
             "VALUES (:proyecto, :fecha, 0, :administracion, :imprevistos, :utilidad)"),
        {"proyecto": id_proyecto, "fecha": date.today().isoformat(),
         "administracion": aiu.get("administracion", 0),
         "imprevistos": aiu.get("imprevistos", 0), "utilidad": aiu.get("utilidad", 0)},
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


def crear_presupuesto(id_usuario, id_proyecto, lineas, aiu=None):
    """Crea presupuesto y agrega sus líneas en una sola transacción."""
    with operational_engine.begin() as connection:
        _exigir_proyecto_accesible(connection, id_proyecto, id_usuario)
        id_presupuesto = _crear_cabecera(connection, id_proyecto, aiu)
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


def agregar_partida_catalogo_presupuesto(
    id_presupuesto, id_usuario, codigo, cantidad, variacion_id=None, lineas_mano_obra=None
):
    """Agrega una partida o variación a precio SQL vigente, sin aceptar precio del cliente."""
    if not isinstance(codigo, str) or not codigo.strip() or len(codigo.strip()) > 50:
        raise ErrorApi(400, "codigo de partida no es válido")
    if variacion_id is not None and (isinstance(variacion_id, bool) or not isinstance(variacion_id, int) or variacion_id <= 0):
        raise ErrorApi(400, "variacion_id debe ser un entero positivo")

    partida = db.session.scalar(
        select(Partida)
        .where(Partida.codigo == codigo.strip())
        .options(selectinload(Partida.variaciones))
    )
    if not partida:
        raise ErrorApi(404, "La partida no existe en el catálogo SQL")
    variacion = None
    if variacion_id is not None:
        variacion = next((opcion for opcion in partida.variaciones if opcion.id == variacion_id), None)
        if not variacion:
            raise ErrorApi(404, "La variación no pertenece a la partida seleccionada")

    with operational_engine.begin() as connection:
        presupuesto = _obtener_presupuesto_accesible(connection, id_presupuesto, id_usuario)
        ciudad = connection.execute(
            text("SELECT ciudad FROM PROYECTOS WHERE id_proyecto=:proyecto"),
            {"proyecto": presupuesto["id_proyecto"]},
        ).scalar() or "Bogotá"
        id_insumo = _crear_o_buscar_insumo_de_partida(connection, partida, ciudad, variacion)
        agregar_linea(connection, id_presupuesto, id_insumo, cantidad, ciudad)

        for linea in lineas_mano_obra or []:
            agregar_linea(connection, id_presupuesto, linea["id_insumo"], linea["cantidad"], ciudad)

        codigo_mano_obra = MANO_OBRA_ASOCIADA.get(partida.codigo)
        if codigo_mano_obra:
            ya_agregada = connection.execute(
                text(
                    "SELECT 1 FROM DETALLE_PRESUPUESTO d JOIN INSUMOS i ON i.id_insumo=d.id_insumo "
                    "WHERE d.id_presupuesto=:presupuesto AND i.nombre_insumo LIKE :prefijo LIMIT 1"
                ),
                {"presupuesto": id_presupuesto, "prefijo": f"{codigo_mano_obra} ·%"},
            ).first()
            mano_obra = db.session.get(Partida, codigo_mano_obra)
            if not ya_agregada and mano_obra:
                id_mano_obra = _crear_o_buscar_insumo_de_partida(connection, mano_obra, ciudad)
                agregar_linea(connection, id_presupuesto, id_mano_obra, cantidad, ciudad)

        recalcular(connection, id_presupuesto)
        return presupuesto_completo(connection, id_presupuesto)


def agregar_mano_obra_asociada(id_presupuesto, id_usuario):
    """Completa montajes de equipo omitidos, derivando partidas y precios del catálogo SQL."""
    with operational_engine.begin() as connection:
        presupuesto = _obtener_presupuesto_accesible(connection, id_presupuesto, id_usuario)
        ciudad = connection.execute(
            text("SELECT ciudad FROM PROYECTOS WHERE id_proyecto=:proyecto"),
            {"proyecto": presupuesto["id_proyecto"]},
        ).scalar() or "Bogotá"
        lineas = connection.execute(
            text(
                "SELECT i.nombre_insumo, d.id_insumo, d.cantidad FROM DETALLE_PRESUPUESTO d "
                "JOIN INSUMOS i ON i.id_insumo=d.id_insumo WHERE d.id_presupuesto=:presupuesto"
            ),
            {"presupuesto": id_presupuesto},
        ).mappings().all()
        for equipo, mano_obra in MANO_OBRA_ASOCIADA.items():
            cantidades = [
                float(linea["cantidad"])
                for linea in lineas if str(linea["nombre_insumo"]).startswith(f"{equipo} ·")
            ]
            existe_mano_obra = any(
                str(linea["nombre_insumo"]).startswith(f"{mano_obra} ·") for linea in lineas
            )
            if not cantidades or existe_mano_obra:
                continue
            partida = db.session.get(Partida, mano_obra)
            if not partida:
                continue
            id_insumo = _crear_o_buscar_insumo_de_partida(connection, partida, ciudad)
            agregar_linea(connection, id_presupuesto, id_insumo, sum(cantidades), ciudad)
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


def actualizar_aiu_presupuesto(id_presupuesto, id_usuario, aiu):
    """Actualiza porcentajes AIU del presupuesto y recalcula su total."""
    with operational_engine.begin() as connection:
        _obtener_presupuesto_accesible(connection, id_presupuesto, id_usuario)
        connection.execute(text(
            "UPDATE PRESUPUESTOS SET porcentaje_administracion=:administracion, "
            "porcentaje_imprevistos=:imprevistos, porcentaje_utilidad=:utilidad "
            "WHERE id_presupuesto=:id"),
            {"administracion": aiu["administracion"], "imprevistos": aiu["imprevistos"],
             "utilidad": aiu["utilidad"], "id": id_presupuesto})
        recalcular(connection, id_presupuesto)
        return presupuesto_completo(connection, id_presupuesto)


def duplicar_presupuesto(id_presupuesto, id_usuario, id_proyecto_destino=None):
    """Duplica líneas y aplica los precios vigentes del catálogo de destino."""
    with operational_engine.begin() as connection:
        original = _obtener_presupuesto_accesible(connection, id_presupuesto, id_usuario)
        destino = original["id_proyecto"] if id_proyecto_destino is None else id_proyecto_destino
        _exigir_proyecto_accesible(connection, destino, id_usuario)
        id_nuevo = _crear_cabecera(connection, destino, {
            "administracion": original["porcentaje_administracion"],
            "imprevistos": original["porcentaje_imprevistos"],
            "utilidad": original["porcentaje_utilidad"],
        })
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
