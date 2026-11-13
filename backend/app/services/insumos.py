"""Casos de uso y persistencia del catálogo de insumos y precios."""

from sqlalchemy import text
import math

from ..database import operational_engine
from ..errors import ErrorApi
from ..utils import en_uso, filas, numero, obtener


def listar_insumos(texto_busqueda="", ciudad="", incluir_inactivos=False):
    """Lista insumos con precio de ciudad cuando existe."""
    consulta = text(
        "SELECT i.id_insumo, i.nombre_insumo, i.unidad_medida, i.activo, "
        "COALESCE(pc.costo_unitario, i.costo_unitario) AS costo_unitario, "
        "CASE WHEN pc.id_precio IS NULL THEN 'referencia_general' ELSE 'precio_ciudad' END AS origen_precio, "
        "q.valor_minimo AS cotizacion_minima, q.valor_maximo AS cotizacion_maxima, "
        "q.valor_referencial AS cotizacion_referencial, q.fecha_referencia AS fecha_cotizacion, "
        "q.fuente AS fuente_cotizacion, q.fuente_url AS url_cotizacion, "
        "q.metodologia AS metodologia_cotizacion, q.incluye_prestaciones AS incluye_prestaciones "
        "FROM INSUMOS i LEFT JOIN PRECIOS_CIUDAD pc "
        "ON pc.id_insumo=i.id_insumo AND pc.ciudad=:ciudad "
        "LEFT JOIN COTIZACIONES_MANO_OBRA q "
        "ON q.id_insumo=i.id_insumo AND q.ciudad=:ciudad "
        "WHERE i.nombre_insumo LIKE :q AND (:inactivos=1 OR COALESCE(i.activo,1)=1) ORDER BY i.nombre_insumo"
    )
    with operational_engine.connect() as connection:
        return filas(connection.execute(consulta, {"q": f"%{texto_busqueda}%", "ciudad": ciudad,
                                                    "inactivos": 1 if incluir_inactivos else 0}))


def obtener_insumo(id_insumo):
    """Obtiene un insumo por identificador."""
    with operational_engine.connect() as connection:
        return obtener(connection, "INSUMOS", "id_insumo", id_insumo)


def _validar_campos(datos):
    """Normaliza nombre, unidad y costo del insumo."""
    if not isinstance(datos.get("nombre_insumo"), str) or not isinstance(datos.get("unidad_medida"), str):
        raise ErrorApi(400, "El nombre y la unidad del insumo deben ser texto")
    nombre = datos["nombre_insumo"].strip()
    unidad = datos["unidad_medida"].strip()
    if not nombre or not unidad or len(nombre) > 150 or len(unidad) > 30:
        raise ErrorApi(400, "El nombre o la unidad del insumo no son válidos")
    return nombre, unidad, numero(datos.get("costo_unitario"), "costo_unitario")


def crear_insumo(datos):
    """Crea un insumo o registra su precio para una ciudad."""
    nombre, unidad, costo = _validar_campos(datos)
    ciudad = datos.get("ciudad")
    with operational_engine.begin() as connection:
        if ciudad:
            if not isinstance(ciudad, str) or not ciudad.strip() or len(ciudad.strip()) > 100:
                raise ErrorApi(400, "La ciudad no es válida")
            ciudad = ciudad.strip()
            existente = connection.execute(
                text("SELECT id_insumo, unidad_medida FROM INSUMOS WHERE nombre_insumo=:nombre"),
                {"nombre": nombre},
            ).mappings().first()
            if existente:
                if existente["unidad_medida"] != unidad:
                    raise ErrorApi(409, "Ya existe un insumo con ese nombre y otra unidad")
                id_insumo = existente["id_insumo"]
            else:
                resultado = connection.execute(
                    text("INSERT INTO INSUMOS (nombre_insumo, unidad_medida, costo_unitario) VALUES (:n, :u, 0)"),
                    {"n": nombre, "u": unidad},
                )
                id_insumo = resultado.lastrowid

            id_precio = connection.execute(
                text("SELECT id_precio FROM PRECIOS_CIUDAD WHERE id_insumo=:id AND ciudad=:ciudad"),
                {"id": id_insumo, "ciudad": ciudad},
            ).scalar()
            if id_precio:
                connection.execute(
                    text("UPDATE PRECIOS_CIUDAD SET costo_unitario=:precio WHERE id_precio=:id"),
                    {"precio": costo, "id": id_precio},
                )
            else:
                connection.execute(
                    text("INSERT INTO PRECIOS_CIUDAD (id_insumo, ciudad, costo_unitario) VALUES (:id, :ciudad, :precio)"),
                    {"id": id_insumo, "ciudad": ciudad, "precio": costo},
                )
            resultado = obtener(connection, "INSUMOS", "id_insumo", id_insumo)
            resultado.update(costo_unitario=costo, origen_precio="precio_ciudad", ciudad=ciudad)
            return resultado

        resultado = connection.execute(
            text("INSERT INTO INSUMOS (nombre_insumo, unidad_medida, costo_unitario) VALUES (:n, :u, :c)"),
            {"n": nombre, "u": unidad, "c": costo},
        )
        return obtener(connection, "INSUMOS", "id_insumo", resultado.lastrowid)


def actualizar_insumo(id_insumo, datos):
    """Actualiza los datos del catálogo para un insumo existente."""
    nombre, unidad, costo = _validar_campos(datos)
    with operational_engine.begin() as connection:
        obtener(connection, "INSUMOS", "id_insumo", id_insumo)
        connection.execute(
            text("UPDATE INSUMOS SET nombre_insumo=:n, unidad_medida=:u, costo_unitario=:c WHERE id_insumo=:i"),
            {"n": nombre, "u": unidad, "c": costo, "i": id_insumo},
        )
        return obtener(connection, "INSUMOS", "id_insumo", id_insumo)


def eliminar_insumo(id_insumo):
    """Elimina un insumo solo cuando no está referenciado en presupuestos."""
    with operational_engine.begin() as connection:
        obtener(connection, "INSUMOS", "id_insumo", id_insumo)
        if en_uso(connection, "SELECT COUNT(*) FROM DETALLE_PRESUPUESTO WHERE id_insumo = :v", id_insumo):
            raise ErrorApi(409, "El insumo está en uso en algún presupuesto")
        connection.execute(text("DELETE FROM COTIZACIONES_MANO_OBRA WHERE id_insumo=:id"), {"id": id_insumo})
        connection.execute(text("DELETE FROM INSUMOS WHERE id_insumo = :id"), {"id": id_insumo})


def actualizar_estado_insumo(id_insumo, activo):
    """Activa o archiva un insumo sin borrar su historial presupuestario."""
    if not isinstance(activo, bool):
        raise ErrorApi(400, "activo debe ser booleano")
    with operational_engine.begin() as connection:
        obtener(connection, "INSUMOS", "id_insumo", id_insumo)
        connection.execute(text("UPDATE INSUMOS SET activo=:activo WHERE id_insumo=:id"),
                           {"activo": 1 if activo else 0, "id": id_insumo})
        return obtener(connection, "INSUMOS", "id_insumo", id_insumo)


def ajustar_precios_masivamente(ciudad, porcentaje, ids_insumos=None):
    """Aplica un ajuste porcentual, auditable y acotado, a precios de una ciudad."""
    if not isinstance(ciudad, str) or not ciudad.strip() or len(ciudad.strip()) > 100:
        raise ErrorApi(400, "Indica una ciudad válida para ajustar sus precios")
    if isinstance(porcentaje, bool):
        raise ErrorApi(400, "El porcentaje debe ser un número entre -100 y 500")
    try:
        porcentaje = float(porcentaje)
    except (TypeError, ValueError) as error:
        raise ErrorApi(400, "El porcentaje debe ser un número entre -100 y 500") from error
    if not math.isfinite(porcentaje) or not -100 <= porcentaje <= 500:
        raise ErrorApi(400, "El porcentaje debe estar entre -100 y 500")
    if ids_insumos is not None and (
        not isinstance(ids_insumos, list)
        or not ids_insumos
        or len(ids_insumos) > 500
        or any(isinstance(item, bool) or not isinstance(item, int) or item < 1 for item in ids_insumos)
    ):
        raise ErrorApi(400, "ids_insumos debe ser una lista de 1 a 500 identificadores positivos")

    with operational_engine.begin() as connection:
        filtros = "ciudad=:ciudad"
        parametros = {"ciudad": ciudad.strip(), "factor": 1 + porcentaje / 100}
        if ids_insumos is not None:
            marcadores = ",".join(f":id_{indice}" for indice, _ in enumerate(ids_insumos))
            filtros += f" AND id_insumo IN ({marcadores})"
            parametros.update({f"id_{indice}": item for indice, item in enumerate(ids_insumos)})
        resultado = connection.execute(
            text(f"UPDATE PRECIOS_CIUDAD SET costo_unitario=ROUND(costo_unitario * :factor, 2) WHERE {filtros}"),
            parametros,
        )
        return {"ciudad": ciudad.strip(), "porcentaje_aplicado": porcentaje, "precios_actualizados": resultado.rowcount}
