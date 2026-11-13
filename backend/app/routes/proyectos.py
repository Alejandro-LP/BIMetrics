"""Endpoints HTTP para proyectos, historial y colaboradores."""

from datetime import date

from flask import Blueprint, jsonify, request, session

from ..errors import ErrorApi
from ..services.proyectos import (
    crear_proyecto,
    crear_codigo_invitacion,
    aceptar_codigo_invitacion,
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
    cliente = request.args.get("cliente", "").strip()
    if len(cliente) > 150:
        raise ErrorApi(400, "El filtro de cliente no puede superar 150 caracteres")
    fechas = {}
    for parametro in ("desde", "hasta"):
        valor = request.args.get(parametro)
        if valor:
            try:
                fechas[parametro] = date.fromisoformat(valor).isoformat()
            except ValueError as error:
                raise ErrorApi(400, f"{parametro} debe tener formato AAAA-MM-DD") from error
        else:
            fechas[parametro] = None
    if fechas["desde"] and fechas["hasta"] and fechas["desde"] > fechas["hasta"]:
        raise ErrorApi(400, "desde no puede ser posterior a hasta")
    return jsonify(obtener_historial_proyecto(id, _usuario_actual(), cliente, fechas["desde"], fechas["hasta"]))


@bp.post("/<int:id>/colaboradores")
def invitar(id):
    """Invita a un usuario a colaborar en el proyecto."""
    datos = pedir(("email",))
    invitar_colaborador(id, _usuario_actual(), datos["email"])
    return jsonify(ok=True, mensaje="Colaborador agregado al proyecto"), 201


@bp.post("/<int:id>/invitaciones")
def crear_invitacion(id):
    """Crea un código de un solo uso para arquitecto, ingeniero o cliente."""
    datos = pedir(("rol",))
    return jsonify(crear_codigo_invitacion(id, _usuario_actual(), datos["rol"])), 201


@bp.post("/invitaciones/aceptar")
def aceptar_invitacion():
    """Canjea un código cuyo rol debe coincidir con el de la cuenta actual."""
    datos = pedir(("codigo",))
    proyecto = aceptar_codigo_invitacion(_usuario_actual(), datos["codigo"])
    return jsonify(ok=True, mensaje="Te uniste al proyecto.", proyecto=proyecto), 200


@bp.delete("/<int:id>")
def eliminar(id):
    """Elimina un proyecto propio."""
    eliminar_proyecto(id, _usuario_actual())
    return "", 204
