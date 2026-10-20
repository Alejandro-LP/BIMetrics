"""Servicio CRUD para gestión de actividades BIM e historiales de importación en MongoDB.

Colección objetivo: `actividades_bim`
Persistencia: Base Documental NoSQL (PyMongo)
"""
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
from bson import ObjectId
from bson.errors import InvalidId
from pymongo.collection import Collection
from pymongo.errors import PyMongoError

from ..database import get_mongo_db
from ..errors import ErrorApi

COLECCION_ACTIVIDADES = "actividades_bim"
logger = logging.getLogger(__name__)


def _obtener_coleccion() -> Collection:
    """Retorna la colección `actividades_bim` desde la base de datos de MongoDB."""
    db = get_mongo_db()
    return db[COLECCION_ACTIVIDADES]


def asegurar_indices_bim() -> None:
    """Ensure the compound index used by the user's recent activity history."""
    try:
        _obtener_coleccion().create_index([("id_usuario", 1), ("fecha_registro", -1)], name="idx_usuario_fecha")
    except PyMongoError:
        # SQL remains available; BIM requests will return a service-unavailable response.
        logger.warning("MongoDB is unavailable; the BIM activity index could not be ensured.", exc_info=True)


def serializar_documento_bim(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Convierte tipos BSON (ObjectId, datetime) a estructuras nativas JSON."""
    if not doc:
        return None
    res = dict(doc)
    if "_id" in res:
        res["id"] = str(res.pop("_id"))
    for clave, valor in res.items():
        if isinstance(valor, datetime):
            res[clave] = valor.isoformat()
        elif isinstance(valor, ObjectId):
            res[clave] = str(valor)
        elif isinstance(valor, dict):
            res[clave] = serializar_documento_bim(valor)
        elif isinstance(valor, list):
            res[clave] = [
                serializar_documento_bim(item) if isinstance(item, dict)
                else (item.isoformat() if isinstance(item, datetime) else str(item) if isinstance(item, ObjectId) else item)
                for item in valor
            ]
    return res


# ------------------------------------------------------------------------------
# OPERACIONES CRUD
# ------------------------------------------------------------------------------

def crear_actividad_bim(datos: Dict[str, Any]) -> Dict[str, Any]:
    """Crea y registra un nuevo documento de log/importación BIM en MongoDB.
    
    Campos esperados en `datos`:
    - id_usuario (int, obligatorio): ID del usuario registrado en SQL.
    - tipo_evento (str, obligatorio): ej. 'importacion_revit_txt', 'importacion_archicad_txt'.
    - software_origen (str, obligatorio): ej. 'Autodesk Revit 2024', 'Graphisoft ArchiCAD 27'.
    - nombre_archivo (str, obligatorio): ej. 'Computos_Vigas.txt'.
    - estado (str, opcional): 'completado' (default), 'advertencia', 'fallido'.
    - id_proyecto (int, opcional): ID del proyecto relacional asociado.
    - detalles_bim (dict, opcional): Metadatos no estructurados de la importación.
    """
    id_usuario = datos.get("id_usuario")
    tipo_evento = datos.get("tipo_evento")
    software_origen = datos.get("software_origen")
    nombre_archivo = datos.get("nombre_archivo")

    if not id_usuario or not isinstance(id_usuario, int):
        raise ErrorApi(400, "'id_usuario' es obligatorio y debe ser un entero válido")
    if not tipo_evento or not str(tipo_evento).strip():
        raise ErrorApi(400, "'tipo_evento' es obligatorio (ej. importacion_revit_txt)")
    if not software_origen or not str(software_origen).strip():
        raise ErrorApi(400, "'software_origen' es obligatorio (ej. Autodesk Revit 2024)")
    if not nombre_archivo or not str(nombre_archivo).strip():
        raise ErrorApi(400, "'nombre_archivo' es obligatorio")

    documento = {
        "id_usuario": id_usuario,
        "id_proyecto": datos.get("id_proyecto"),
        "tipo_evento": str(tipo_evento).strip().lower(),
        "software_origen": str(software_origen).strip(),
        "nombre_archivo": str(nombre_archivo).strip(),
        "estado": datos.get("estado", "completado"),
        "detalles_bim": datos.get("detalles_bim") or {},
        "fecha_registro": datetime.now(timezone.utc),
        "fecha_actualizacion": datetime.now(timezone.utc),
    }

    coleccion = _obtener_coleccion()
    resultado = coleccion.insert_one(documento)
    documento["_id"] = resultado.inserted_id
    return serializar_documento_bim(documento)


def obtener_actividad_bim(id_actividad: str) -> Optional[Dict[str, Any]]:
    """Consulta un documento de actividad BIM por su ObjectId hex string."""
    try:
        obj_id = ObjectId(id_actividad)
    except (InvalidId, TypeError):
        raise ErrorApi(400, f"'{id_actividad}' no es un ObjectId de MongoDB válido")

    coleccion = _obtener_coleccion()
    doc = coleccion.find_one({"_id": obj_id})
    if not doc:
        return None
    return serializar_documento_bim(doc)


def listar_actividades_bim(
    id_usuario: Optional[int] = None,
    tipo_evento: Optional[str] = None,
    limite: int = 10,
    skip: int = 0
) -> List[Dict[str, Any]]:
    """Consulta una lista paginada de actividades BIM con orden descendente por fecha."""
    filtro: Dict[str, Any] = {}
    if id_usuario is not None:
        filtro["id_usuario"] = id_usuario
    if tipo_evento:
        filtro["tipo_evento"] = tipo_evento

    limite = max(1, min(100, int(limite)))
    skip = max(0, int(skip))

    coleccion = _obtener_coleccion()
    cursor = coleccion.find(filtro).sort("fecha_registro", -1).skip(skip).limit(limite)
    return [serializar_documento_bim(doc) for doc in cursor]


def actualizar_actividad_bim(id_actividad: str, datos_actualizacion: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Actualiza campos específicos de un documento de actividad BIM por su ObjectId."""
    try:
        obj_id = ObjectId(id_actividad)
    except (InvalidId, TypeError):
        raise ErrorApi(400, f"'{id_actividad}' no es un ObjectId de MongoDB válido")

    # Prevenir sobreescritura de campos inmutables
    campos_a_actualizar = {
        k: v for k, v in datos_actualizacion.items()
        if k not in ("_id", "id", "fecha_registro", "id_usuario")
    }

    if not campos_a_actualizar:
        raise ErrorApi(400, "No se proporcionaron campos modificables válidos para actualizar")

    campos_a_actualizar["fecha_actualizacion"] = datetime.now(timezone.utc)

    coleccion = _obtener_coleccion()
    resultado = coleccion.find_one_and_update(
        {"_id": obj_id},
        {"$set": campos_a_actualizar},
        return_document=True
    )
    if not resultado:
        return None
    return serializar_documento_bim(resultado)


def eliminar_actividad_bim(id_actividad: str) -> bool:
    """Elimina permanentemente un documento de actividad BIM por su ObjectId."""
    try:
        obj_id = ObjectId(id_actividad)
    except (InvalidId, TypeError):
        raise ErrorApi(400, f"'{id_actividad}' no es un ObjectId de MongoDB válido")

    coleccion = _obtener_coleccion()
    resultado = coleccion.delete_one({"_id": obj_id})
    return resultado.deleted_count > 0
