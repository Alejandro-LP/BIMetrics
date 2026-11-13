"""Endpoints HTTP para sesión y perfil de usuario."""

from flask import Blueprint, jsonify, request, session

from ..errors import ErrorApi
from ..services.autenticacion import (
    actualizar_perfil_usuario,
    actualizar_preferencias_usuario,
    autenticar_usuario,
    obtener_preferencias_usuario,
    obtener_sesion_usuario,
    registrar_usuario,
    solicitar_restablecimiento,
    restablecer_password,
)
from ..services.usuarios_mongo import obtener_version_sesion
from ..utils import pedir

bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@bp.post("/registro")
def registrar():
    """Crea una cuenta e inicia su sesión."""
    usuario = registrar_usuario(pedir(("nombre_completo", "email", "password", "rol")))
    session.clear()
    session["id_usuario"] = usuario["id_usuario"]
    session["version_sesion"] = obtener_version_sesion(usuario["id_usuario"])
    return jsonify(usuario), 201


@bp.post("/login")
def iniciar_sesion():
    """Valida credenciales e inicia una sesión autenticada."""
    datos = pedir(("email", "password"))
    usuario = autenticar_usuario(datos["email"], datos["password"])
    session.clear()
    session["id_usuario"] = usuario["id_usuario"]
    session["version_sesion"] = obtener_version_sesion(usuario["id_usuario"])
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


@bp.post("/solicitar-restablecimiento")
def solicitar_reset():
    """Solicita un enlace sin revelar si la cuenta existe."""
    datos = request.get_json(silent=True)
    if not isinstance(datos, dict):
        raise ErrorApi(400, "El cuerpo debe ser un objeto JSON")
    resultado = solicitar_restablecimiento(datos.get("email"))
    respuesta = {"mensaje": "Si el correo corresponde a una cuenta, recibirás instrucciones para restablecer la contraseña."}
    if resultado and resultado.get("enlace_desarrollo"):
        respuesta["enlace_desarrollo"] = resultado["enlace_desarrollo"]
        respuesta["mensaje"] = "Enlace local creado. Ábrelo para definir una contraseña nueva; en producción se enviará por correo."
    return jsonify(respuesta)


@bp.post("/restablecer-password")
def completar_reset():
    """Consume un enlace válido de un solo uso."""
    datos = request.get_json(silent=True)
    if not isinstance(datos, dict):
        raise ErrorApi(400, "El cuerpo debe ser un objeto JSON")
    restablecer_password(datos.get("token"), datos.get("password"))
    return jsonify(mensaje="Contraseña actualizada. Inicia sesión con tu nueva contraseña.")


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
    actualizado = actualizar_perfil_usuario(id_usuario, datos)
    if datos.get("new_password"):
        session["version_sesion"] = int(session.get("version_sesion", 1)) + 1
    return jsonify(actualizado)


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
