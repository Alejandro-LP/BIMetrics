"""Casos de uso administrativos de identidades persistidas en MongoDB."""

from contextlib import contextmanager

from pymongo.errors import DuplicateKeyError
from sqlalchemy import text
from werkzeug.security import generate_password_hash

from ..config import ROLES
from ..database import operational_engine
from ..errors import ErrorApi
from .usuarios_mongo import (
    crear_o_actualizar_admin,
    eliminar_usuario as borrar_usuario_documento,
    listar_usuarios as listar_documentos_usuarios,
    obtener_usuario as obtener_documento_usuario,
    obtener_usuario_por_email,
)


def validar_usuario(datos, id_solicitante, requiere_password=False):
    """Valida perfil y limita la asignación de roles administrativos."""
    campos = ("nombre_completo", "email", "rol")
    if any(campo not in datos or datos[campo] in (None, "") for campo in campos):
        raise ErrorApi(400, "Faltan campos: nombre_completo, email, rol")
    if not isinstance(datos["rol"], str) or datos["rol"] not in ROLES:
        raise ErrorApi(400, f"'rol' debe ser uno de: {', '.join(sorted(ROLES))}")
    if not isinstance(datos["nombre_completo"], str) or not isinstance(datos["email"], str):
        raise ErrorApi(400, "El nombre y el correo deben ser texto")
    nombre = datos["nombre_completo"].strip()
    email = datos["email"].strip().lower()
    if not nombre or len(nombre) > 150 or not email or len(email) > 254 or "@" not in email:
        raise ErrorApi(400, "El nombre o el correo no son válidos")
    if datos["rol"] == "administrador":
        solicitante = obtener_documento_usuario(id_solicitante) if id_solicitante else None
        if not solicitante or solicitante["rol"] != "administrador":
            raise ErrorApi(403, "Solo un administrador puede asignar ese rol")
    password = datos.get("password", "")
    if requiere_password and not isinstance(password, str):
        raise ErrorApi(400, "La contraseña debe ser texto")
    if requiere_password and not 10 <= len(password) <= 128:
        raise ErrorApi(400, "La contraseña debe tener entre 10 y 128 caracteres")
    if password and (not isinstance(password, str) or not 10 <= len(password) <= 128):
        raise ErrorApi(400, "La contraseña debe tener entre 10 y 128 caracteres")
    resultado = {"n": nombre, "e": email, "r": datos["rol"]}
    if password:
        resultado["password_hash"] = generate_password_hash(password)
    return resultado


def listar_usuarios(rol=None):
    """Lista perfiles públicos, opcionalmente filtrados por rol."""
    return listar_documentos_usuarios(rol)


def obtener_usuario(id_usuario):
    """Obtiene el perfil administrativo de un usuario."""
    usuario = obtener_documento_usuario(id_usuario)
    if not usuario:
        raise ErrorApi(404, f"No existe usuario con id {id_usuario}")
    return usuario


@contextmanager
def _cambio_administrativo(id_solicitante):
    """Serializa cambios en SQLite y vuelve a comprobar el rol del solicitante."""
    with operational_engine.begin() as connection:
        if connection.dialect.name == "sqlite":
            connection.exec_driver_sql("BEGIN IMMEDIATE")
        solicitante = obtener_documento_usuario(id_solicitante)
        if not solicitante or solicitante["rol"] != "administrador":
            raise ErrorApi(403, "Solo un administrador puede gestionar usuarios")
        yield connection


def crear_usuario(datos, id_solicitante):
    """Crea una cuenta en el repositorio MongoDB."""
    with _cambio_administrativo(id_solicitante):
        if obtener_usuario_por_email(datos["e"]):
            raise ErrorApi(409, "Ese correo ya está asociado a otra cuenta")
        try:
            return crear_o_actualizar_admin(datos, password_hash=datos["password_hash"])
        except DuplicateKeyError as error:
            raise ErrorApi(409, "No se pudo crear la cuenta. Revisa si el correo ya está en uso.") from error


def actualizar_usuario(id_usuario, datos, id_solicitante):
    """Actualiza un perfil existente y valida unicidad de correo."""
    with _cambio_administrativo(id_solicitante):
        if id_usuario == id_solicitante and datos["r"] != "administrador":
            raise ErrorApi(409, "Tu cuenta debe conservar el rol de administrador")
        anterior = obtener_usuario(id_usuario)
        existente = obtener_usuario_por_email(datos["e"])
        if existente and existente["id_usuario"] != id_usuario:
            raise ErrorApi(409, "Ese correo ya está asociado a otra cuenta")
        try:
            actualizado = crear_o_actualizar_admin(
                datos, id_usuario=id_usuario, password_hash=datos.get("password_hash"),
                invalidar_sesiones=anterior["rol"] != datos["r"],
            )
        except DuplicateKeyError as error:
            raise ErrorApi(409, "Ese correo ya está asociado a otra cuenta") from error
        if not actualizado:
            raise ErrorApi(404, "El usuario no existe")
        return actualizado


def eliminar_usuario(id_usuario, id_solicitante):
    """Elimina una identidad que no sea propietaria de proyectos."""
    with _cambio_administrativo(id_solicitante) as connection:
        if id_usuario == id_solicitante:
            raise ErrorApi(409, "No puedes eliminar la cuenta con la que has iniciado sesión")
        obtener_usuario(id_usuario)
        proyectos_propios = connection.execute(
            text("SELECT COUNT(*) FROM PROYECTOS WHERE id_usuario=:id"), {"id": id_usuario}
        ).scalar()
        if proyectos_propios:
            raise ErrorApi(409, "Esta cuenta es propietaria de proyectos y no puede eliminarse mientras los conserve")
        connection.execute(
            text("DELETE FROM PROYECTO_COLABORADORES WHERE id_usuario=:id OR invitado_por=:id"),
            {"id": id_usuario},
        )
        borrar_usuario_documento(id_usuario)
