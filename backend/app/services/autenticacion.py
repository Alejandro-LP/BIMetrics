"""Casos de uso de registro, autenticación y perfil de usuario en MongoDB."""

import re
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from flask import current_app
from werkzeug.security import check_password_hash, generate_password_hash

from ..errors import ErrorApi
from .correo import correo_restablecimiento_disponible, enviar_enlace_restablecimiento, modo_restablecimiento_local
from .usuarios_mongo import (
    autenticar,
    crear_usuario,
    obtener_documento_usuario,
    obtener_usuario,
    obtener_usuario_por_email,
    actualizar_perfil as persistir_perfil,
    actualizar_preferencias as persistir_preferencias,
    obtener_preferencias as consultar_preferencias,
    buscar_usuario_para_restablecer,
    guardar_restablecimiento,
    eliminar_restablecimiento,
    actualizar_password_restablecida,
)

_EMAIL = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
_ROLES_REGISTRO = {"arquitecto", "ingeniero", "cliente"}


def registrar_usuario(datos):
    """Valida y crea una identidad con credenciales y preferencias iniciales."""
    campos = ("nombre_completo", "email", "password", "rol")
    if not all(isinstance(datos.get(campo), str) for campo in campos):
        raise ErrorApi(400, "Nombre, correo, contraseña y rol deben ser texto")
    nombre = datos["nombre_completo"].strip()
    email = datos["email"].strip().lower()
    password = datos["password"]
    rol = datos["rol"]
    if datos.get("autoriza_datos") is not True:
        raise ErrorApi(400, "Debes autorizar el tratamiento de datos para crear una cuenta")
    if not 2 <= len(nombre) <= 150:
        raise ErrorApi(400, "El nombre debe tener entre 2 y 150 caracteres")
    if len(email) > 150 or not _EMAIL.match(email):
        raise ErrorApi(400, "Ingresa un correo válido")
    if not 10 <= len(password) <= 128:
        raise ErrorApi(400, "La contraseña debe tener entre 10 y 128 caracteres")
    if rol not in _ROLES_REGISTRO:
        raise ErrorApi(400, "El rol debe ser arquitecto, ingeniero o cliente")
    if obtener_usuario_por_email(email):
        raise ErrorApi(409, "Ese correo ya está asociado a otra cuenta")
    return crear_usuario(
        nombre, email, generate_password_hash(password), rol, datos["autoriza_datos"]
    )


def autenticar_usuario(email, password):
    """Comprueba las credenciales almacenadas en el documento de usuario."""
    if not isinstance(email, str) or not isinstance(password, str):
        raise ErrorApi(400, "Correo y contraseña deben ser texto")
    return autenticar(email, password)


def solicitar_restablecimiento(email):
    """Genera y entrega un token de un solo uso, sin revelar si existe el correo."""
    if not isinstance(email, str) or len(email.strip()) > 150 or not _EMAIL.fullmatch(email.strip()):
        raise ErrorApi(400, "Ingresa un correo válido")
    if not correo_restablecimiento_disponible():
        raise ErrorApi(503, "La recuperación por correo no está disponible en este momento.")
    usuario = obtener_usuario_por_email(email.strip().lower())
    if not usuario:
        return

    ahora = datetime.now(timezone.utc)
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    if not guardar_restablecimiento(usuario, token_hash, ahora, ahora + timedelta(minutes=30)):
        return
    if modo_restablecimiento_local():
        return {"enlace_desarrollo": f"{current_app.config['APP_BASE_URL']}/restablecer?token={token}"}
    if not enviar_enlace_restablecimiento(usuario["email"], token):
        eliminar_restablecimiento(usuario["id_usuario"], token_hash)
    return None


def restablecer_password(token, nueva_password):
    """Consume un token expirable y reemplaza el hash de contraseña del usuario."""
    if not isinstance(token, str) or not 32 <= len(token) <= 128:
        raise ErrorApi(400, "El enlace de restablecimiento no es válido o ya expiró")
    if not isinstance(nueva_password, str) or not 10 <= len(nueva_password) <= 128:
        raise ErrorApi(400, "La contraseña debe tener entre 10 y 128 caracteres")
    ahora = datetime.now(timezone.utc)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    usuario, filtro = buscar_usuario_para_restablecer(token_hash, ahora)
    if not usuario:
        raise ErrorApi(400, "El enlace de restablecimiento no es válido o ya expiró")
    nuevo_hash = generate_password_hash(nueva_password)
    ahora = datetime.now(timezone.utc)
    if "restablecimiento.expira_en" in filtro:
        filtro["restablecimiento.expira_en"] = {"$gt": ahora}
    actualizada = actualizar_password_restablecida(
        usuario, filtro, nuevo_hash, ahora
    )
    if not actualizada:
        raise ErrorApi(400, "No se pudo restablecer la contraseña. Solicita un enlace nuevo")


def obtener_sesion_usuario(id_usuario):
    """Obtiene el perfil público asociado al identificador de sesión."""
    if not id_usuario:
        raise ErrorApi(401, "Inicia sesión para continuar")
    usuario = obtener_usuario(id_usuario)
    if not usuario:
        raise ErrorApi(401, "La sesión ya no es válida")
    return usuario


def actualizar_perfil_usuario(id_usuario, datos):
    """Verifica la contraseña actual y actualiza perfil y contraseña opcional."""
    campos = ("nombre_completo", "email", "current_password", "new_password")
    if not all(isinstance(datos.get(campo, ""), str) for campo in campos):
        raise ErrorApi(400, "Los datos del perfil deben ser texto")
    nombre = datos["nombre_completo"].strip()
    email = datos["email"].strip().lower()
    password_actual = datos["current_password"]
    password_nueva = datos.get("new_password", "")
    if not 2 <= len(nombre) <= 150:
        raise ErrorApi(400, "El nombre debe tener entre 2 y 150 caracteres")
    if len(email) > 150 or not _EMAIL.match(email):
        raise ErrorApi(400, "Ingresa un correo válido")
    if password_nueva and not 10 <= len(password_nueva) <= 128:
        raise ErrorApi(400, "La nueva contraseña debe tener entre 10 y 128 caracteres")

    documento = obtener_documento_usuario(id_usuario)
    if not documento or not check_password_hash(documento["password_hash"], password_actual):
        raise ErrorApi(400, "La contraseña actual no coincide")
    existente = obtener_usuario_por_email(email)
    if existente and existente["id_usuario"] != int(id_usuario):
        raise ErrorApi(409, "Ese correo ya está asociado a otra cuenta")
    hash_nuevo = generate_password_hash(password_nueva) if password_nueva else None
    actualizado = persistir_perfil(id_usuario, nombre, email, hash_nuevo)
    if not actualizado:
        raise ErrorApi(404, "El usuario no existe")
    return actualizado


def obtener_preferencias_usuario(id_usuario):
    """Devuelve las preferencias dinámicas guardadas en el perfil Mongo."""
    return consultar_preferencias(id_usuario)


def actualizar_preferencias_usuario(id_usuario, preferencias):
    """Valida y persiste preferencias dinámicas del usuario."""
    return persistir_preferencias(id_usuario, preferencias)
