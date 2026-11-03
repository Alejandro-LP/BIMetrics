"""Endpoints HTTP para consulta y mantenimiento del catálogo de insumos."""

from flask import Blueprint, jsonify, request

from ..services.insumos import (
    actualizar_insumo,
    crear_insumo,
    eliminar_insumo,
    listar_insumos,
    obtener_insumo,
)
from ..utils import pedir

bp = Blueprint("insumos", __name__, url_prefix="/api/insumos")
CAMPOS = ("nombre_insumo", "unidad_medida", "costo_unitario")


@bp.get("")
def listar():
    """Lista insumos aplicando búsqueda y ciudad opcionales."""
    texto = request.args.get("q", "").strip()
    ciudad = request.args.get("ciudad", "").strip()
    return jsonify(listar_insumos(texto, ciudad))


@bp.get("/<int:id>")
def ver(id):
    """Devuelve un insumo por su identificador."""
    return jsonify(obtener_insumo(id))


@bp.post("")
def crear():
    """Crea un insumo o actualiza el precio asociado a una ciudad."""
    datos = pedir(CAMPOS)
    return jsonify(crear_insumo(datos)), 201


@bp.put("/<int:id>")
def actualizar(id):
    """Actualiza los datos principales de un insumo."""
    datos = pedir(CAMPOS)
    return jsonify(actualizar_insumo(id, datos))


@bp.delete("/<int:id>")
def eliminar(id):
    """Elimina un insumo que no esté en uso."""
    eliminar_insumo(id)
    return "", 204
