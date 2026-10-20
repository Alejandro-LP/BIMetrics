"""Blueprint para endpoints de actividades BIM e historial de importaciones NoSQL.

Implementa la arquitectura políglota de BIMetrics combinando:
1. SQL Relacional: Perfil, roles RBAC y existencia del usuario en la tabla `USUARIOS`.
2. NoSQL Documental: Logs de telemetría, cómputos e importaciones en MongoDB (`actividades_bim`).
"""
from collections import Counter
from flask import Blueprint, jsonify, request
from sqlalchemy import text

from ..database import engine
from ..errors import ErrorApi
from ..services.actividades_bim import (
    actualizar_actividad_bim,
    crear_actividad_bim,
    eliminar_actividad_bim,
    listar_actividades_bim,
    obtener_actividad_bim,
)

bp = Blueprint("actividades_bim", __name__, url_prefix="/api/actividades-bim")


# ------------------------------------------------------------------------------
# 1. ENDPOINT POLÍGLOTA HÍBRIDO (SQL + NoSQL)
# ------------------------------------------------------------------------------
@bp.get("/usuario/<int:id_usuario>")
def obtener_resumen_hibrido_usuario(id_usuario: int):
    """Endpoint políglota central:
    
    1. Consulta la base relacional (SQL) para obtener perfil estructurado y rol RBAC.
    2. Consulta MongoDB (NoSQL) para obtener las últimas 10 actividades e importaciones BIM.
    3. Retorna un JSON unificado enriquecido con métricas agregadas.
    """
    # Paso 1: Consultar datos estructurados del usuario en la base relacional (SQL)
    with engine.connect() as con:
        usuario_row = con.execute(
            text("SELECT id_usuario, nombre_completo, email, rol FROM USUARIOS WHERE id_usuario = :id"),
            {"id": id_usuario}
        ).mappings().first()

    if not usuario_row:
        raise ErrorApi(404, f"No existe usuario registrado con id {id_usuario} en la base principal")

    usuario_sql = dict(usuario_row)

    # Paso 2: Consultar logs documentales no estructurados en MongoDB (NoSQL)
    # Obtenemos las últimas 10 actividades de importación/auditoría ordenadas desc por fecha
    limite = int(request.args.get("limite", 10))
    actividades_nosql = listar_actividades_bim(id_usuario=id_usuario, limite=limite)

    # Paso 3: Calcular métricas sintéticas sobre la marcha
    total_recientes = len(actividades_nosql)
    ultima_actividad = actividades_nosql[0]["fecha_registro"] if total_recientes > 0 else None
    
    softwares = [act.get("software_origen") for act in actividades_nosql if act.get("software_origen")]
    software_mas_usado = Counter(softwares).most_common(1)[0][0] if softwares else None

    # Paso 4: Generar y retornar el payload JSON unificado
    return jsonify({
        "usuario": usuario_sql,
        "resumen_bim": {
            "total_actividades_recientes": total_recientes,
            "software_mas_frecuente": software_mas_usado,
            "ultima_actividad": ultima_actividad,
        },
        "actividades_recientes": actividades_nosql,
    })


# ------------------------------------------------------------------------------
# 2. OPERACIONES CRUD SOBRE ACTIVIDADES BIM (MongoDB)
# ------------------------------------------------------------------------------

@bp.post("")
def registrar_actividad():
    """Registra un nuevo log de importación o actividad BIM en MongoDB.
    Valida previamente la existencia del usuario en la base relacional (integridad políglota).
    """
    datos = request.get_json(silent=True) or {}
    id_usuario = datos.get("id_usuario")

    if not id_usuario:
        raise ErrorApi(400, "El campo 'id_usuario' es obligatorio")

    # Validación de integridad referencial cruzada (Cross-database integrity check)
    with engine.connect() as con:
        existe_usuario = con.execute(
            text("SELECT 1 FROM USUARIOS WHERE id_usuario = :id"),
            {"id": id_usuario}
        ).scalar()

    if not existe_usuario:
        raise ErrorApi(404, f"No se puede registrar actividad: el usuario {id_usuario} no existe en SQL")

    actividad_creada = crear_actividad_bim(datos)
    return jsonify(actividad_creada), 201


@bp.get("/<string:id_actividad>")
def ver_actividad(id_actividad: str):
    """Consulta una actividad específica por su ObjectId de MongoDB."""
    actividad = obtener_actividad_bim(id_actividad)
    if not actividad:
        raise ErrorApi(404, f"No se encontró ninguna actividad con ID '{id_actividad}'")
    return jsonify(actividad)


@bp.put("/<string:id_actividad>")
def editar_actividad(id_actividad: str):
    """Actualiza datos parciales de una actividad BIM existente."""
    datos = request.get_json(silent=True) or {}
    actividad_actualizada = actualizar_actividad_bim(id_actividad, datos)
    if not actividad_actualizada:
        raise ErrorApi(404, f"No se encontró ninguna actividad con ID '{id_actividad}' para actualizar")
    return jsonify(actividad_actualizada)


@bp.delete("/<string:id_actividad>")
def borrar_actividad(id_actividad: str):
    """Elimina un documento de actividad de MongoDB."""
    eliminado = eliminar_actividad_bim(id_actividad)
    if not eliminado:
        raise ErrorApi(404, f"No se encontró la actividad con ID '{id_actividad}' para eliminar")
    return jsonify({"mensaje": "Actividad BIM eliminada exitosamente", "id": id_actividad})
