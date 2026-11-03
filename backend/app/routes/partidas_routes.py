"""Endpoints de solo lectura para el catálogo de partidas."""
from flask import Blueprint, jsonify, request

from ..services.partida_service import buscar_partidas, listar_partidas, obtener_partida

bp = Blueprint("partidas", __name__, url_prefix="/api/partidas")


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
