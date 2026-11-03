"""Endpoints HTTP para sesión y perfil de usuario."""

from flask import Blueprint, jsonify, session

from ..errors import ErrorApi
from ..services.autenticacion import (
    actualizar_perfil_usuario,
    actualizar_preferencias_usuario,
    autenticar_usuario,
    obtener_preferencias_usuario,
    obtener_sesion_usuario,
    registrar_usuario,
)
from ..utils import pedir

bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@bp.post("/registro")
def registrar():
    """Crea una cuenta e inicia su sesión."""
    usuario = registrar_usuario(pedir(("nombre_completo", "email", "password", "rol")))
    session.clear()
    session["id_usuario"] = usuario["id_usuario"]
    return jsonify(usuario), 201


@bp.post("/login")
def iniciar_sesion():
    """Valida credenciales e inicia una sesión autenticada."""
    datos = pedir(("email", "password"))
    usuario = autenticar_usuario(datos["email"], datos["password"])
    session.clear()
    session["id_usuario"] = usuario["id_usuario"]
    return jsonify(usuario)


@bp.get("/sesion")
def sesion_actual():
    """Devuelve el perfil asociado a la sesión vigente."""
    try:
        usuario = obtener_sesion_usuario(session.get("id_usuario"))
    except ErrorApi as error:
        if error.code == 401:
            session.clear()
        raise
    return jsonify(usuario)


@bp.post("/logout")
def cerrar_sesion():
    """Invalida la sesión actual."""
    session.clear()
    return jsonify(mensaje="Sesión cerrada")


@bp.put("/perfil")
def actualizar_perfil():
    """Actualiza el perfil del usuario autenticado."""
    id_usuario = session.get("id_usuario")
    if not id_usuario:
        raise ErrorApi(401, "Inicia sesión para continuar")
    datos = pedir(("nombre_completo", "email", "current_password"))
    return jsonify(actualizar_perfil_usuario(id_usuario, datos))


@bp.get("/preferencias")
def preferencias():
    """Devuelve preferencias dinámicas del usuario autenticado."""
    id_usuario = session.get("id_usuario")
    if not id_usuario:
        raise ErrorApi(401, "Inicia sesión para continuar")
    return jsonify(preferencias=obtener_preferencias_usuario(id_usuario))


@bp.put("/preferencias")
def actualizar_preferencias():
    """Reemplaza las preferencias dinámicas del usuario autenticado."""
    id_usuario = session.get("id_usuario")
    if not id_usuario:
        raise ErrorApi(401, "Inicia sesión para continuar")
    datos = pedir(("preferencias",))
    resultado = actualizar_preferencias_usuario(id_usuario, datos["preferencias"])
    return jsonify(preferencias=resultado)
