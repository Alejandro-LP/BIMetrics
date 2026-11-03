"""Endpoints HTTP para el historial de actividades BIM."""

from flask import Blueprint, jsonify, request, session

from ..errors import ErrorApi
from ..services.actividades_bim_api import (
    actualizar_actividad,
    eliminar_actividad,
    obtener_actividad,
    obtener_resumen_usuario,
    registrar_actividad,
)
from ..services.actividades_bim import listar_actividades_bim

bp = Blueprint("actividades_bim", __name__, url_prefix="/api/actividades-bim")


def _cuerpo_json():
    """Lee un objeto JSON del request o devuelve un error HTTP 400."""
    datos = request.get_json(silent=True)
    if not isinstance(datos, dict):
        raise ErrorApi(400, "El cuerpo de la solicitud debe ser un objeto JSON")
    return datos


@bp.get("/usuario/<int:id_usuario>")
def resumen_usuario(id_usuario):
    """Devuelve perfil y actividad BIM reciente del usuario solicitado."""
    try:
        limite = int(request.args.get("limite", 10))
    except (TypeError, ValueError) as error:
        raise ErrorApi(400, "El límite debe ser un número entero") from error
    limite = max(1, min(100, limite))
    resultado = obtener_resumen_usuario(
        id_usuario, session.get("id_usuario"), limite, listar_actividades=listar_actividades_bim
    )
    return jsonify(resultado)


@bp.post("")
def crear():
    """Registra una actividad BIM para el usuario autenticado."""
    resultado = registrar_actividad(_cuerpo_json(), session.get("id_usuario"))
    return jsonify(resultado), 201


@bp.get("/<string:id_actividad>")
def ver(id_actividad):
    """Devuelve una actividad visible para el usuario autenticado."""
    return jsonify(obtener_actividad(id_actividad, session.get("id_usuario")))


@bp.put("/<string:id_actividad>")
def actualizar(id_actividad):
    """Actualiza campos editables de una actividad propia."""
    resultado = actualizar_actividad(
        id_actividad, _cuerpo_json(), session.get("id_usuario")
    )
    return jsonify(resultado)


@bp.delete("/<string:id_actividad>")
def eliminar(id_actividad):
    """Elimina una actividad propia."""
    eliminar_actividad(id_actividad, session.get("id_usuario"))
    return jsonify({"mensaje": "Actividad BIM eliminada exitosamente", "id": id_actividad})
