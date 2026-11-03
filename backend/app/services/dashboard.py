"""Consultas y composición de métricas del panel principal."""

from pymongo.errors import PyMongoError
from sqlalchemy import text

from ..database import operational_engine
from ..errors import ErrorApi
from .usuarios_mongo import obtener_usuario
from .actividades_bim import listar_actividades_bim


def obtener_resumen(id_usuario):
    """Obtiene métricas SQL y la última actividad BIM del usuario."""
    consulta = text(
        """
        SELECT
          (SELECT COUNT(DISTINCT p.id_proyecto)
           FROM PROYECTOS p
           WHERE p.id_usuario = :id_usuario OR EXISTS (
             SELECT 1 FROM PROYECTO_COLABORADORES c
             WHERE c.id_proyecto = p.id_proyecto AND c.id_usuario = :id_usuario
           )) AS total_proyectos,
          COALESCE((
            SELECT SUM(b.costo_total)
            FROM PRESUPUESTOS b
            JOIN PROYECTOS p ON p.id_proyecto = b.id_proyecto
            WHERE (p.id_usuario = :id_usuario OR EXISTS (
              SELECT 1 FROM PROYECTO_COLABORADORES c
              WHERE c.id_proyecto = p.id_proyecto AND c.id_usuario = :id_usuario
            )) AND NOT EXISTS (
              SELECT 1 FROM PRESUPUESTOS reciente
              WHERE reciente.id_proyecto = b.id_proyecto
                AND (reciente.fecha_calculo > b.fecha_calculo OR
                  (reciente.fecha_calculo = b.fecha_calculo AND reciente.id_presupuesto > b.id_presupuesto))
            )
          ), 0) AS presupuesto_total,
          (SELECT COUNT(*) FROM INSUMOS) AS total_insumos
        """
    )

    with operational_engine.connect() as connection:
        metricas = connection.execute(consulta, {"id_usuario": id_usuario}).mappings().one()

    usuario = obtener_usuario(id_usuario)
    if not usuario:
        raise ErrorApi(401, "La sesión no corresponde a una cuenta activa")

    actividad = None
    mongodb_disponible = True
    try:
        actividades = listar_actividades_bim(id_usuario=id_usuario, limite=1)
        actividad = actividades[0] if actividades else None
    except PyMongoError:
        mongodb_disponible = False

    return {
        "usuario": {"nombre_completo": usuario["nombre_completo"], "rol": usuario["rol"]},
        "resumen": {
            "total_proyectos": int(metricas["total_proyectos"] or 0),
            "presupuesto_total": float(metricas["presupuesto_total"] or 0),
            "total_insumos": int(metricas["total_insumos"] or 0),
            "ultima_actividad_bim": actividad,
            "mongodb_disponible": mongodb_disponible,
        },
    }
