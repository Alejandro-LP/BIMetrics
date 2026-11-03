"""Endpoints HTTP para proyectos, historial y colaboradores."""

from flask import Blueprint, jsonify, session

from ..errors import ErrorApi
from ..services.proyectos import (
    crear_proyecto,
    eliminar_proyecto,
    invitar_colaborador,
    listar_proyectos,
    obtener_historial_proyecto,
)
from ..utils import pedir

bp = Blueprint("proyectos", __name__, url_prefix="/api/proyectos")


def _usuario_actual():
    """Obtiene el identificador de usuario de la sesión HTTP."""
    id_usuario = session.get("id_usuario")
    if not id_usuario:
        raise ErrorApi(401, "Inicia sesión para continuar")
    return id_usuario


@bp.get("")
def listar():
    """Lista los proyectos visibles para el usuario autenticado."""
    return jsonify(listar_proyectos(_usuario_actual()))


@bp.post("")
def crear():
    """Crea un proyecto para el usuario autenticado."""
    datos = pedir(("nombre_obra",))
    return jsonify(crear_proyecto(_usuario_actual(), datos)), 201


@bp.get("/<int:id>/presupuestos")
def historial(id):
    """Lista el historial presupuestario de un proyecto accesible."""
    return jsonify(obtener_historial_proyecto(id, _usuario_actual()))


@bp.post("/<int:id>/colaboradores")
def invitar(id):
    """Invita a un usuario a colaborar en el proyecto."""
    datos = pedir(("email",))
    invitar_colaborador(id, _usuario_actual(), datos["email"])
    return jsonify(ok=True, mensaje="Colaborador agregado al proyecto"), 201


@bp.delete("/<int:id>")
def eliminar(id):
    """Elimina un proyecto propio."""
    eliminar_proyecto(id, _usuario_actual())
    return "", 204
