"""Endpoints HTTP para administración de usuarios."""

from flask import Blueprint, jsonify, request, session

from ..errors import ErrorApi
from ..services.usuarios import (
    actualizar_usuario,
    crear_usuario,
    eliminar_usuario,
    listar_usuarios,
    obtener_usuario,
    validar_usuario,
)

bp = Blueprint("usuarios", __name__, url_prefix="/api/usuarios")


@bp.get("")
def listar():
    """Devuelve usuarios, con filtro opcional por rol."""
    return jsonify(listar_usuarios(request.args.get("rol")))


@bp.get("/<int:id>")
def ver(id):
    """Devuelve el usuario solicitado."""
    return jsonify(obtener_usuario(id))


@bp.post("")
def crear():
    """Valida y crea un usuario."""
    datos = request.get_json(silent=True)
    if not isinstance(datos, dict):
        raise ErrorApi(400, "El cuerpo de la solicitud debe ser un objeto JSON")
    usuario = validar_usuario(datos, session.get("id_usuario"), requiere_password=True)
    return jsonify(crear_usuario(usuario)), 201


@bp.put("/<int:id>")
def actualizar(id):
    """Valida y actualiza un usuario."""
    datos = request.get_json(silent=True)
    if not isinstance(datos, dict):
        raise ErrorApi(400, "El cuerpo de la solicitud debe ser un objeto JSON")
    usuario = validar_usuario(datos, session.get("id_usuario"))
    return jsonify(actualizar_usuario(id, usuario))


@bp.delete("/<int:id>")
def eliminar(id):
    """Elimina el usuario si no tiene proyectos asociados."""
    eliminar_usuario(id)
    return "", 204
