"""Endpoints HTTP del dashboard."""

from flask import Blueprint, jsonify, session

from ..errors import ErrorApi
from ..services.dashboard import obtener_resumen

bp = Blueprint("dashboard", __name__, url_prefix="/api/dashboard")


@bp.get("/resumen")
def resumen():
    """Devuelve métricas consolidadas del usuario autenticado."""
    id_usuario = session.get("id_usuario")
    if not id_usuario:
        raise ErrorApi(401, "Inicia sesión para consultar el dashboard")
    return jsonify(obtener_resumen(id_usuario))
