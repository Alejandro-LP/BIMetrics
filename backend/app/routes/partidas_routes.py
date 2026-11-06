"""Endpoints del catálogo de partidas con modificaciones restringidas a administración."""
from decimal import Decimal, InvalidOperation
from flask import Blueprint, jsonify, request, session

from ..catalog_models import Partida, VariacionOpcion
from ..errors import ErrorApi
from ..extensions import db
from ..services.partida_service import buscar_partidas, listar_partidas, obtener_partida, serializar_partida
from ..services.usuarios_mongo import obtener_usuario

bp = Blueprint("partidas", __name__, url_prefix="/api/partidas")


def _exigir_administrador():
    """Los cambios del catálogo maestro están reservados al administrador."""
    id_usuario = session.get("id_usuario")
    usuario = obtener_usuario(id_usuario) if id_usuario else None
    if not usuario or usuario.get("rol") != "administrador":
        raise ErrorApi(403, "Solo un administrador puede modificar el catálogo maestro")


def _validar_partida(datos, codigo_ruta=None):
    if not isinstance(datos, dict):
        raise ErrorApi(400, "El cuerpo de la solicitud debe ser un objeto JSON")
    codigo = codigo_ruta or datos.get("codigo")
    unidad = datos.get("unidad")
    descripcion = datos.get("descripcion")
    if not all(isinstance(valor, str) and valor.strip() for valor in (codigo, unidad, descripcion)):
        raise ErrorApi(400, "codigo, unidad y descripcion son obligatorios")
    codigo, unidad, descripcion = codigo.strip(), unidad.strip(), descripcion.strip()
    if len(codigo) > 50 or len(unidad) > 50 or len(descripcion) > 10000:
        raise ErrorApi(400, "Uno de los campos excede el tamaño permitido")
    try:
        precio = Decimal(str(datos.get("precio_defecto", 0)))
    except (InvalidOperation, TypeError, ValueError) as error:
        raise ErrorApi(400, "precio_defecto debe ser un número válido") from error
    if not precio.is_finite() or precio < 0:
        raise ErrorApi(400, "precio_defecto debe ser finito y no negativo")
    variaciones = datos.get("variaciones", [])
    if not isinstance(variaciones, list):
        raise ErrorApi(400, "variaciones debe ser una lista")
    validadas = []
    for item in variaciones:
        if not isinstance(item, dict) or not isinstance(item.get("tipo"), str) or not item["tipo"].strip():
            raise ErrorApi(400, "Cada variación debe incluir un tipo de texto")
        precio_variacion = item.get("precio")
        if precio_variacion is not None:
            try:
                precio_variacion = Decimal(str(precio_variacion))
            except (InvalidOperation, TypeError, ValueError) as error:
                raise ErrorApi(400, "El precio de variación debe ser numérico") from error
            if not precio_variacion.is_finite() or precio_variacion < 0:
                raise ErrorApi(400, "El precio de variación debe ser finito y no negativo")
        for campo in ("opcion", "parametro", "valor_probado"):
            valor = item.get(campo)
            if valor is not None and not isinstance(valor, str):
                raise ErrorApi(400, f"{campo} debe ser texto")
        if "es_defecto" in item and not isinstance(item["es_defecto"], bool):
            raise ErrorApi(400, "es_defecto debe ser booleano")
        validadas.append({
            "tipo": item["tipo"].strip(),
            "opcion": item.get("opcion"),
            "parametro": item.get("parametro"),
            "valor_probado": item.get("valor_probado"),
            "es_defecto": item.get("es_defecto", False) is True,
            "precio": precio_variacion,
        })
    return codigo, unidad, descripcion, precio, validadas


def _paginacion():
    try:
        limit = int(request.args.get("limit", 50))
        offset = int(request.args.get("offset", 0))
    except (TypeError, ValueError):
        return None, (jsonify(error="limit y offset deben ser enteros"), 400)
    if limit < 1 or limit > 200 or offset < 0:
        return None, (jsonify(error="limit debe estar entre 1 y 200 y offset no puede ser negativo"), 400)
    return (limit, offset), None


@bp.get("")
def listar():
    pagina, error = _paginacion()
    if error:
        return error
    return jsonify(listar_partidas(*pagina))


@bp.post("")
def crear():
    _exigir_administrador()
    codigo, unidad, descripcion, precio, variaciones = _validar_partida(request.get_json(silent=True))
    if db.session.get(Partida, codigo):
        raise ErrorApi(409, "Ya existe una partida con ese código")
    partida = Partida(codigo=codigo, unidad=unidad, descripcion=descripcion, precio_defecto=precio)
    partida.variaciones = [VariacionOpcion(**item) for item in variaciones]
    db.session.add(partida)
    db.session.commit()
    return jsonify(serializar_partida(partida, incluir_variaciones=True)), 201


@bp.get("/buscar")
def buscar():
    texto = request.args.get("q", "").strip()
    if not texto:
        return jsonify(error="El parámetro q es obligatorio"), 400
    pagina, error = _paginacion()
    if error:
        return error
    return jsonify(buscar_partidas(texto, *pagina))


@bp.get("/<string:codigo>")
def detalle(codigo):
    partida = obtener_partida(codigo)
    if partida is None:
        return jsonify(error="Partida no encontrada"), 404
    return jsonify(partida)


@bp.put("/<string:codigo>")
def actualizar(codigo):
    _exigir_administrador()
    partida = db.session.get(Partida, codigo)
    if not partida:
        raise ErrorApi(404, "Partida no encontrada")
    datos = request.get_json(silent=True)
    _, unidad, descripcion, precio, variaciones = _validar_partida(datos, codigo)
    partida.unidad = unidad
    partida.descripcion = descripcion
    partida.precio_defecto = precio
    if "variaciones" in datos:
        partida.variaciones = [VariacionOpcion(**item) for item in variaciones]
    db.session.commit()
    return jsonify(serializar_partida(partida, incluir_variaciones=True))


@bp.delete("/<string:codigo>")
def eliminar(codigo):
    _exigir_administrador()
    partida = db.session.get(Partida, codigo)
    if not partida:
        raise ErrorApi(404, "Partida no encontrada")
    db.session.delete(partida)
    db.session.commit()
    return "", 204
