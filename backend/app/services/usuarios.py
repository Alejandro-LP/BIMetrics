"""Casos de uso administrativos de identidades persistidas en MongoDB."""

from sqlalchemy import text

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


def validar_usuario(datos, id_solicitante):
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
    return {"n": nombre, "e": email, "r": datos["rol"]}


def listar_usuarios(rol=None):
    """Lista perfiles públicos, opcionalmente filtrados por rol."""
    return listar_documentos_usuarios(rol)


def obtener_usuario(id_usuario):
    """Obtiene el perfil administrativo de un usuario."""
    usuario = obtener_documento_usuario(id_usuario)
    if not usuario:
        raise ErrorApi(404, f"No existe usuario con id {id_usuario}")
    return usuario


def crear_usuario(datos):
    """Crea una cuenta administrativa en el repositorio MongoDB."""
    if obtener_usuario_por_email(datos["e"]):
        raise ErrorApi(409, "Ese correo ya está asociado a otra cuenta")
    return crear_o_actualizar_admin(datos)


def actualizar_usuario(id_usuario, datos):
    """Actualiza un perfil existente y valida unicidad de correo."""
    obtener_usuario(id_usuario)
    existente = obtener_usuario_por_email(datos["e"])
    if existente and existente["id_usuario"] != int(id_usuario):
        raise ErrorApi(409, "Ese correo ya está asociado a otra cuenta")
    actualizado = crear_o_actualizar_admin(datos, id_usuario=id_usuario)
    if not actualizado:
        raise ErrorApi(404, f"No existe usuario con id {id_usuario}")
    return actualizado


def eliminar_usuario(id_usuario):
    """Elimina una identidad que no sea propietaria de proyectos."""
    obtener_usuario(id_usuario)
    with operational_engine.begin() as connection:
        proyectos_propios = connection.execute(
            text("SELECT COUNT(*) FROM PROYECTOS WHERE id_usuario=:id"), {"id": id_usuario}
        ).scalar()
        if proyectos_propios:
            raise ErrorApi(409, "El usuario tiene proyectos asociados")
        connection.execute(
            text("DELETE FROM PROYECTO_COLABORADORES WHERE id_usuario=:id OR invitado_por=:id"),
            {"id": id_usuario},
        )
    borrar_usuario_documento(id_usuario)
