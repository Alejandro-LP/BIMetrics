"""Repositorio MongoDB para identidades, credenciales y perfiles de usuario."""

from datetime import datetime, timezone

from pymongo import ASCENDING, ReturnDocument
from pymongo.errors import PyMongoError
from werkzeug.security import check_password_hash

from ..database import get_mongo_db
from ..errors import ErrorApi

COLECCION_USUARIOS = "usuarios"
COLECCION_CONTADORES = "contadores"


def _coleccion():
    return get_mongo_db("users")[COLECCION_USUARIOS]


def asegurar_indices_usuarios():
    """Crea índices únicos para la identidad pública y el correo de acceso."""
    try:
        coleccion = _coleccion()
        coleccion.create_index([("id_usuario", ASCENDING)], unique=True, name="uq_usuario_id")
        coleccion.create_index([("email", ASCENDING)], unique=True, name="uq_usuario_email")
    except PyMongoError:
        from flask import current_app

        current_app.logger.warning("MongoDB de usuarios no disponible; no se pudieron verificar índices.", exc_info=True)


def _publico(documento):
    if not documento:
        return None
    return {
        "id_usuario": documento["id_usuario"],
        "nombre_completo": documento["nombre_completo"],
        "email": documento["email"],
        "rol": documento["rol"],
    }


def crear_usuario(nombre, email, password_hash, rol, autoriza_datos):
    """Crea una identidad Mongo con identificador entero compatible con BIMetrics."""
    database = get_mongo_db("users")
    secuencia = database[COLECCION_CONTADORES].find_one_and_update(
        {"_id": "id_usuario"},
        {"$inc": {"valor": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    id_usuario = secuencia["valor"]
    documento = {
        "id_usuario": id_usuario,
        "nombre_completo": nombre,
        "email": email,
        "password_hash": password_hash,
        "rol": rol,
        "preferencias": {},
        "autorizacion_datos": {
            "aceptada": bool(autoriza_datos),
            "version": "2026-10-15",
            "fecha": datetime.now(timezone.utc),
        },
        "fecha_creacion": datetime.now(timezone.utc),
        "fecha_actualizacion": datetime.now(timezone.utc),
    }
    _coleccion().insert_one(documento)
    return _publico(documento)


def obtener_usuario(id_usuario):
    """Busca un perfil por su identificador numérico."""
    return _publico(_coleccion().find_one({"id_usuario": int(id_usuario)}))


def obtener_usuarios(id_usuarios):
    """Obtiene en una sola consulta los perfiles públicos de varios usuarios."""
    ids = {int(id_usuario) for id_usuario in id_usuarios if id_usuario is not None}
    cursor = _coleccion().find({"id_usuario": {"$in": list(ids)}})
    return {documento["id_usuario"]: _publico(documento) for documento in cursor}


def obtener_documento_usuario(id_usuario):
    """Obtiene el documento interno para verificar credenciales y permisos."""
    return _coleccion().find_one({"id_usuario": int(id_usuario)})


def obtener_usuario_por_email(email):
    """Busca una identidad por correo normalizado."""
    documento = _coleccion().find_one({"email": email.strip().lower()})
    return documento


def autenticar(email, password):
    """Comprueba el hash de contraseña sin devolver credenciales."""
    documento = obtener_usuario_por_email(email)
    if (
        not documento
        or not documento.get("password_hash")
        or not check_password_hash(documento["password_hash"], password)
    ):
        raise ErrorApi(401, "Correo o contraseña incorrectos")
    return _publico(documento)


def actualizar_perfil(id_usuario, nombre, email, password_hash=None):
    """Actualiza datos de perfil y contraseña opcional."""
    cambios = {"nombre_completo": nombre, "email": email, "fecha_actualizacion": datetime.now(timezone.utc)}
    if password_hash:
        cambios["password_hash"] = password_hash
    resultado = _coleccion().find_one_and_update(
        {"id_usuario": int(id_usuario)}, {"$set": cambios}, return_document=ReturnDocument.AFTER
    )
    return _publico(resultado)


def listar_usuarios(rol=None):
    """Lista perfiles públicos, opcionalmente filtrados por rol."""
    filtro = {"rol": rol} if rol else {}
    cursor = _coleccion().find(filtro).sort("nombre_completo", ASCENDING)
    return [_publico(documento) for documento in cursor]


def crear_o_actualizar_admin(datos, id_usuario=None, password_hash=None):
    """Crea o actualiza usuarios desde el módulo administrativo."""
    coleccion = _coleccion()
    email = datos["e"]
    cambios = {"nombre_completo": datos["n"], "email": email, "rol": datos["r"],
               "fecha_actualizacion": datetime.now(timezone.utc)}
    if id_usuario is None:
        database = get_mongo_db("users")
        secuencia = database[COLECCION_CONTADORES].find_one_and_update(
            {"_id": "id_usuario"}, {"$inc": {"valor": 1}}, upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        documento = {**cambios, "id_usuario": secuencia["valor"], "password_hash": password_hash, "preferencias": {},
            "autorizacion_datos": {"aceptada": True, "version": "admin"},
            "fecha_creacion": datetime.now(timezone.utc)}
        coleccion.insert_one(documento)
        return _publico(documento)
    if password_hash:
        cambios["password_hash"] = password_hash
    actualizado = coleccion.find_one_and_update(
        {"id_usuario": int(id_usuario)}, {"$set": cambios}, return_document=ReturnDocument.AFTER
    )
    return _publico(actualizado)


def obtener_preferencias(id_usuario):
    """Devuelve las preferencias dinámicas del perfil."""
    documento = _coleccion().find_one({"id_usuario": int(id_usuario)}, {"preferencias": 1})
    if not documento:
        raise ErrorApi(404, f"No existe usuario con id {id_usuario}")
    return documento.get("preferencias") or {}


def actualizar_preferencias(id_usuario, preferencias):
    """Reemplaza el objeto flexible de preferencias para un usuario."""
    if not isinstance(preferencias, dict):
        raise ErrorApi(400, "preferencias debe ser un objeto JSON")

    def claves_validas(valor):
        if isinstance(valor, dict):
            return all(
                isinstance(clave, str) and clave and "." not in clave and not clave.startswith("$")
                and claves_validas(contenido)
                for clave, contenido in valor.items()
            )
        if isinstance(valor, list):
            return all(claves_validas(elemento) for elemento in valor)
        return True

    if not claves_validas(preferencias):
        raise ErrorApi(400, "Las claves de preferencias no son válidas")
    resultado = _coleccion().update_one(
        {"id_usuario": int(id_usuario)},
        {"$set": {"preferencias": preferencias, "fecha_actualizacion": datetime.now(timezone.utc)}},
    )
    if not resultado.matched_count:
        raise ErrorApi(404, f"No existe usuario con id {id_usuario}")
    return preferencias


def eliminar_usuario(id_usuario):
    """Elimina una identidad de usuario por id."""
    resultado = _coleccion().delete_one({"id_usuario": int(id_usuario)})
    if not resultado.deleted_count:
        raise ErrorApi(404, f"No existe usuario con id {id_usuario}")
