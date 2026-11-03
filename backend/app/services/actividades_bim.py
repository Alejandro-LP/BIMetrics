"""Servicio CRUD para gestión de actividades BIM e historiales de importación en MongoDB.

Colección objetivo: `actividades_bim`
Persistencia: Base Documental NoSQL (PyMongo)
"""
from datetime import datetime, timezone
import logging
import json
from typing import Any, Dict, List, Optional
from bson import ObjectId
from bson.errors import InvalidId
from pymongo.collection import Collection
from pymongo.errors import PyMongoError

from ..database import get_mongo_db
from ..errors import ErrorApi

COLECCION_ACTIVIDADES = "actividades_bim"
ESTADOS_VALIDOS = {"completado", "advertencia", "fallido"}
MAX_DETALLES_BYTES = 1_000_000
logger = logging.getLogger(__name__)


def _validar_detalles(detalles):
    """Limita el payload flexible para evitar documentos inválidos o excesivos."""
    if not isinstance(detalles, dict):
        raise ErrorApi(400, "detalles_bim debe ser un objeto JSON")
    try:
        contenido = json.dumps(detalles, ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise ErrorApi(400, "detalles_bim solo puede contener valores JSON válidos") from error
    if len(contenido) > MAX_DETALLES_BYTES:
        raise ErrorApi(413, "detalles_bim supera el límite de 1 MB")
    return detalles


def _validar_texto(datos, campo, maximo, obligatorio=False):
    """Valida y normaliza campos de texto persistidos en MongoDB."""
    valor = datos.get(campo)
    if valor is None and not obligatorio:
        return None
    if not isinstance(valor, str):
        raise ErrorApi(400, f"{campo} debe ser texto")
    valor = valor.strip()
    if (obligatorio and not valor) or len(valor) > maximo:
        raise ErrorApi(400, f"{campo} no es válido")
    return valor


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
    - id_usuario (int, obligatorio): ID de la identidad almacenada en MongoDB.
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

    if isinstance(id_usuario, bool) or not isinstance(id_usuario, int) or id_usuario <= 0:
        raise ErrorApi(400, "'id_usuario' es obligatorio y debe ser un entero válido")
    tipo_evento = _validar_texto(datos, "tipo_evento", 100, obligatorio=True)
    software_origen = _validar_texto(datos, "software_origen", 120, obligatorio=True)
    nombre_archivo = _validar_texto(datos, "nombre_archivo", 255, obligatorio=True)
    estado = datos.get("estado", "completado")
    if not isinstance(estado, str) or estado not in ESTADOS_VALIDOS:
        raise ErrorApi(400, "estado debe ser completado, advertencia o fallido")
    id_proyecto = datos.get("id_proyecto")
    if id_proyecto is not None and (
        isinstance(id_proyecto, bool) or not isinstance(id_proyecto, int) or id_proyecto <= 0
    ):
        raise ErrorApi(400, "id_proyecto debe ser un entero positivo")

    documento = {
        "id_usuario": id_usuario,
        "id_proyecto": datos.get("id_proyecto"),
        "tipo_evento": tipo_evento.lower(),
        "software_origen": software_origen,
        "nombre_archivo": nombre_archivo,
        "estado": estado,
        "detalles_bim": _validar_detalles(datos.get("detalles_bim") or {}),
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


def actualizar_actividad_bim(
    id_actividad: str, datos_actualizacion: Dict[str, Any], id_usuario: Optional[int] = None
) -> Optional[Dict[str, Any]]:
    """Actualiza campos específicos de un documento de actividad BIM por su ObjectId."""
    try:
        obj_id = ObjectId(id_actividad)
    except (InvalidId, TypeError):
        raise ErrorApi(400, f"'{id_actividad}' no es un ObjectId de MongoDB válido")

    # Solo se actualizan campos del contrato de la API; nunca se aceptan rutas Mongo arbitrarias.
    campos_a_actualizar = {}
    if "tipo_evento" in datos_actualizacion:
        campos_a_actualizar["tipo_evento"] = _validar_texto(datos_actualizacion, "tipo_evento", 100, True).lower()
    if "software_origen" in datos_actualizacion:
        campos_a_actualizar["software_origen"] = _validar_texto(datos_actualizacion, "software_origen", 120, True)
    if "nombre_archivo" in datos_actualizacion:
        campos_a_actualizar["nombre_archivo"] = _validar_texto(datos_actualizacion, "nombre_archivo", 255, True)
    if "estado" in datos_actualizacion:
        estado = datos_actualizacion["estado"]
        if not isinstance(estado, str) or estado not in ESTADOS_VALIDOS:
            raise ErrorApi(400, "estado debe ser completado, advertencia o fallido")
        campos_a_actualizar["estado"] = estado
    if "detalles_bim" in datos_actualizacion:
        campos_a_actualizar["detalles_bim"] = _validar_detalles(datos_actualizacion["detalles_bim"])
    if "id_proyecto" in datos_actualizacion:
        id_proyecto = datos_actualizacion["id_proyecto"]
        if id_proyecto is not None and (
            isinstance(id_proyecto, bool) or not isinstance(id_proyecto, int) or id_proyecto <= 0
        ):
            raise ErrorApi(400, "id_proyecto debe ser un entero positivo o null")
        campos_a_actualizar["id_proyecto"] = id_proyecto

    if not campos_a_actualizar:
        raise ErrorApi(400, "No se proporcionaron campos modificables válidos para actualizar")

    campos_a_actualizar["fecha_actualizacion"] = datetime.now(timezone.utc)

    coleccion = _obtener_coleccion()
    filtro = {"_id": obj_id}
    if id_usuario is not None:
        filtro["id_usuario"] = int(id_usuario)
    resultado = coleccion.find_one_and_update(
        filtro,
        {"$set": campos_a_actualizar},
        return_document=True
    )
    if not resultado:
        return None
    return serializar_documento_bim(resultado)


def eliminar_actividad_bim(id_actividad: str, id_usuario: Optional[int] = None) -> bool:
    """Elimina permanentemente un documento de actividad BIM por su ObjectId."""
    try:
        obj_id = ObjectId(id_actividad)
    except (InvalidId, TypeError):
        raise ErrorApi(400, f"'{id_actividad}' no es un ObjectId de MongoDB válido")

    coleccion = _obtener_coleccion()
    filtro = {"_id": obj_id}
    if id_usuario is not None:
        filtro["id_usuario"] = int(id_usuario)
    resultado = coleccion.delete_one(filtro)
    return resultado.deleted_count > 0
