"""Endpoints HTTP para gestión y exportación de presupuestos."""

from flask import Blueprint, jsonify, request, send_file, session

from ..errors import ErrorApi
from ..services.excel import exportar_presupuesto_excel
from ..services.presupuestos_api import (
    agregar_linea_presupuesto,
    calcular_presupuesto,
    crear_presupuesto,
    duplicar_presupuesto,
    listar_presupuestos,
    obtener_presupuesto,
    quitar_linea_presupuesto,
)
from ..utils import pedir

bp = Blueprint("presupuestos", __name__, url_prefix="/api/presupuestos")


def _usuario_actual():
    """Obtiene el usuario autenticado para las operaciones de presupuesto."""
    id_usuario = session.get("id_usuario")
    if not id_usuario:
        raise ErrorApi(401, "Inicia sesión para continuar")
    return id_usuario


@bp.get("")
def listar():
    """Lista presupuestos visibles, con filtro opcional por proyecto."""
    id_proyecto = request.args.get("id_proyecto") or None
    return jsonify(listar_presupuestos(_usuario_actual(), id_proyecto))


@bp.get("/<int:id>")
def ver(id):
    """Devuelve el detalle completo de un presupuesto accesible."""
    return jsonify(obtener_presupuesto(id, _usuario_actual()))


@bp.get("/<int:id>/excel")
def exportar_excel(id):
    """Genera y descarga el presupuesto como archivo XLSX."""
    presupuesto = obtener_presupuesto(id, _usuario_actual())
    stream = exportar_presupuesto_excel(presupuesto)
    nombre_seguro = "".join(
        caracter for caracter in (presupuesto.get("nombre_obra") or "BIMetrics")
        if caracter.isalnum() or caracter in (" ", "_", "-")
    ).strip().replace(" ", "_")
    return send_file(
        stream,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=f"Presupuesto_{nombre_seguro}_{id}.xlsx",
    )


@bp.post("")
def crear():
    """Crea un presupuesto con sus líneas iniciales opcionales."""
    datos = pedir(("id_proyecto",))
    lineas = datos.get("detalle", [])
    if lineas is None:
        lineas = []
    if not isinstance(lineas, list) or any(not isinstance(linea, dict) for linea in lineas):
        raise ErrorApi(400, "El detalle debe ser una lista de partidas")
    resultado = crear_presupuesto(_usuario_actual(), datos["id_proyecto"], lineas)
    return jsonify(resultado), 201


@bp.post("/<int:id>/detalle")
def agregar_detalle(id):
    """Agrega un insumo y, opcionalmente, sus líneas de mano de obra en una operación."""
    datos = pedir(("id_insumo", "cantidad"))
    lineas_mano_obra = datos.get("lineas_mano_obra", [])
    if not isinstance(lineas_mano_obra, list) or any(
        not isinstance(linea, dict) or not linea.get("id_insumo") or linea.get("cantidad") is None
        for linea in lineas_mano_obra
    ):
        raise ErrorApi(400, "lineas_mano_obra debe ser una lista de insumos y cantidades válidas")
    resultado = agregar_linea_presupuesto(
        id,
        _usuario_actual(),
        datos["id_insumo"],
        datos["cantidad"],
        lineas_mano_obra=lineas_mano_obra,
    )
    return jsonify(resultado), 201


@bp.delete("/<int:id>/detalle/<int:id_detalle>")
def quitar_detalle(id, id_detalle):
    """Elimina una línea del presupuesto."""
    return jsonify(quitar_linea_presupuesto(id, id_detalle, _usuario_actual()))


@bp.post("/<int:id>/calcular")
def calcular(id):
    """Recalcula el costo total del presupuesto."""
    total = calcular_presupuesto(id, _usuario_actual())
    return jsonify(id_presupuesto=id, costo_total=total)


@bp.post("/<int:id>/duplicar")
def duplicar(id):
    """Duplica el presupuesto, opcionalmente en otro proyecto accesible."""
    datos = request.get_json(silent=True)
    if datos is None:
        datos = {}
    elif not isinstance(datos, dict):
        raise ErrorApi(400, "El cuerpo de la solicitud debe ser un objeto JSON")
    resultado = duplicar_presupuesto(id, _usuario_actual(), datos.get("id_proyecto"))
    return jsonify(resultado), 201
