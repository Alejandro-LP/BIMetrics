"""Casos de uso que coordinan identidad SQL y actividad documental BIM."""

from collections import Counter

from sqlalchemy import text

from ..database import operational_engine
from ..errors import ErrorApi
from .usuarios_mongo import obtener_usuario
from .actividades_bim import (
    actualizar_actividad_bim,
    crear_actividad_bim,
    eliminar_actividad_bim,
    listar_actividades_bim,
    obtener_actividad_bim,
)


def _rol_usuario(id_usuario):
    """Consulta en MongoDB el rol de un usuario autenticado."""
    if not id_usuario:
        raise ErrorApi(401, "Inicia sesión para continuar")
    usuario = obtener_usuario(id_usuario)
    return usuario["rol"] if usuario else None


def _validar_proyecto(id_proyecto, id_usuario):
    """Comprueba que la obra SQL pertenezca al usuario o esté compartida con él."""
    if id_proyecto is None:
        return None
    if isinstance(id_proyecto, bool) or not isinstance(id_proyecto, int) or id_proyecto <= 0:
        raise ErrorApi(400, "id_proyecto debe ser un entero positivo")
    consulta = text(
        "SELECT 1 FROM PROYECTOS p WHERE p.id_proyecto=:proyecto AND "
        "(p.id_usuario=:usuario OR EXISTS (SELECT 1 FROM PROYECTO_COLABORADORES c "
        "WHERE c.id_proyecto=p.id_proyecto AND c.id_usuario=:usuario))"
    )
    with operational_engine.connect() as connection:
        existe = connection.execute(
            consulta, {"proyecto": id_proyecto, "usuario": id_usuario}
        ).first()
    if not existe:
        raise ErrorApi(404, "La obra asociada no existe o no pertenece al usuario")
    return id_proyecto


def _exigir_propietario(actividad, id_usuario_solicitante):
    """Oculta recursos ajenos para evitar revelar su existencia."""
    if not actividad:
        raise ErrorApi(404, "No se encontró la actividad BIM")
    if actividad.get("id_usuario") != id_usuario_solicitante:
        if _rol_usuario(id_usuario_solicitante) != "administrador":
            raise ErrorApi(404, "No se encontró la actividad BIM")
    return actividad


def obtener_resumen_usuario(
    id_usuario_objetivo, id_usuario_solicitante, limite, listar_actividades=listar_actividades_bim
):
    """Compone el perfil de MongoDB con el historial BIM de MongoDB."""
    if id_usuario_objetivo != id_usuario_solicitante and _rol_usuario(id_usuario_solicitante) != "administrador":
        raise ErrorApi(404, "No existe usuario registrado con ese identificador")
    fila = obtener_usuario(id_usuario_objetivo)
    if not fila:
        raise ErrorApi(404, f"No existe usuario registrado con id {id_usuario_objetivo} en la base principal")

    actividades = listar_actividades(id_usuario=id_usuario_objetivo, limite=limite)
    software = [actividad.get("software_origen") for actividad in actividades if actividad.get("software_origen")]
    return {
        "usuario": fila,
        "resumen_bim": {
            "total_actividades_recientes": len(actividades),
            "software_mas_frecuente": Counter(software).most_common(1)[0][0] if software else None,
            "ultima_actividad": actividades[0].get("fecha_registro") if actividades else None,
        },
        "actividades_recientes": actividades,
    }


def registrar_actividad(datos, id_usuario_solicitante):
    """Valida la identidad MongoDB y el acceso SQL opcional a la obra asociada."""
    id_usuario = datos.get("id_usuario")
    if not id_usuario or isinstance(id_usuario, bool):
        raise ErrorApi(400, "El campo 'id_usuario' es obligatorio")
    try:
        id_usuario = int(id_usuario)
    except (TypeError, ValueError, OverflowError) as error:
        raise ErrorApi(400, "El campo 'id_usuario' debe ser un entero") from error
    if id_usuario != id_usuario_solicitante and _rol_usuario(id_usuario_solicitante) != "administrador":
        raise ErrorApi(403, "No puedes registrar actividad para otro usuario")
    if not obtener_usuario(id_usuario):
        raise ErrorApi(404, f"No existe la identidad MongoDB con id {id_usuario}")
    datos_validados = {**datos, "id_usuario": id_usuario}
    datos_validados["id_proyecto"] = _validar_proyecto(datos.get("id_proyecto"), id_usuario)
    return crear_actividad_bim(datos_validados)


def obtener_actividad(id_actividad, id_usuario_solicitante):
    """Obtiene una actividad si pertenece al usuario o es administrador."""
    return _exigir_propietario(obtener_actividad_bim(id_actividad), id_usuario_solicitante)


def actualizar_actividad(id_actividad, datos, id_usuario_solicitante):
    """Actualiza una actividad después de verificar su propietario."""
    existente = _exigir_propietario(obtener_actividad_bim(id_actividad), id_usuario_solicitante)
    datos_validados = dict(datos)
    if "id_proyecto" in datos_validados:
        datos_validados["id_proyecto"] = _validar_proyecto(
            datos_validados["id_proyecto"], existente["id_usuario"]
        )
    actividad = actualizar_actividad_bim(
        id_actividad, datos_validados, id_usuario=existente["id_usuario"]
    )
    if not actividad:
        raise ErrorApi(404, f"No se encontró ninguna actividad con ID '{id_actividad}' para actualizar")
    return actividad


def eliminar_actividad(id_actividad, id_usuario_solicitante):
    """Elimina una actividad después de verificar su propietario."""
    existente = _exigir_propietario(obtener_actividad_bim(id_actividad), id_usuario_solicitante)
    if not eliminar_actividad_bim(id_actividad, id_usuario=existente["id_usuario"]):
        raise ErrorApi(404, f"No se encontró la actividad con ID '{id_actividad}' para eliminar")
