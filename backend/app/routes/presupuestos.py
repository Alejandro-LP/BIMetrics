"""Endpoints HTTP para gestión y exportación de presupuestos."""

from flask import Blueprint, jsonify, request, send_file, session
import math

from ..errors import ErrorApi
from ..services.excel import exportar_presupuesto_excel
from ..services.pdf import exportar_presupuesto_pdf
from ..services.word import exportar_presupuesto_word
from ..services.presupuestos_api import (
    agregar_linea_presupuesto,
    agregar_partida_catalogo_presupuesto,
    agregar_mano_obra_asociada,
    calcular_presupuesto,
    crear_presupuesto,
    actualizar_aiu_presupuesto,
    duplicar_presupuesto,
    listar_presupuestos,
    obtener_presupuesto,
    quitar_linea_presupuesto,
)
from ..services.importacion_txt_bim import leer_txt_bim
from ..utils import pedir

bp = Blueprint("presupuestos", __name__, url_prefix="/api/presupuestos")


def _validar_aiu(datos, obligatorio=False):
    if obligatorio and "aiu" not in datos:
        raise ErrorApi(400, "aiu es obligatorio")
    aiu = datos.get("aiu", {})
    if not isinstance(aiu, dict):
        raise ErrorApi(400, "aiu debe ser un objeto JSON")
    resultado = {}
    for campo in ("administracion", "imprevistos", "utilidad"):
        valor = aiu.get(campo, 0)
        if isinstance(valor, bool):
            raise ErrorApi(400, f"El porcentaje de {campo} debe ser un número entre 0 y 100")
        try:
            valor = float(valor)
        except (TypeError, ValueError):
            raise ErrorApi(400, f"El porcentaje de {campo} debe ser un número entre 0 y 100") from None
        if not math.isfinite(valor) or not 0 <= valor <= 100:
            raise ErrorApi(400, f"El porcentaje de {campo} debe ser un número entre 0 y 100")
        resultado[campo] = valor
    return resultado


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


@bp.put("/<int:id>/aiu")
def actualizar_aiu(id):
    """Configura administración, imprevistos y utilidad para el costo directo."""
    datos = request.get_json(silent=True)
    if not isinstance(datos, dict):
        raise ErrorApi(400, "El cuerpo de la solicitud debe ser un objeto JSON")
    return jsonify(actualizar_aiu_presupuesto(id, _usuario_actual(), _validar_aiu(datos, obligatorio=True)))


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


@bp.get("/<int:id>/pdf")
def exportar_pdf(id):
    """Genera un PDF del presupuesto accesible; no firma digitalmente el archivo."""
    presupuesto = obtener_presupuesto(id, _usuario_actual())
    stream = exportar_presupuesto_pdf(presupuesto)
    nombre_seguro = "".join(
        caracter for caracter in (presupuesto.get("nombre_obra") or "BIMetrics")
        if caracter.isalnum() or caracter in (" ", "_", "-")
    ).strip().replace(" ", "_")
    return send_file(
        stream,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"Presupuesto_{nombre_seguro}_{id}.pdf",
    )


@bp.get("/<int:id>/word")
def exportar_word(id):
    """Genera un documento Word editable sin simular firma digital."""
    presupuesto = obtener_presupuesto(id, _usuario_actual())
    stream = exportar_presupuesto_word(presupuesto)
    nombre_seguro = "".join(
        caracter for caracter in (presupuesto.get("nombre_obra") or "BIMetrics")
        if caracter.isalnum() or caracter in (" ", "_", "-")
    ).strip().replace(" ", "_")
    return send_file(
        stream,
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        as_attachment=True,
        download_name=f"Presupuesto_{nombre_seguro}_{id}.docx",
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
    resultado = crear_presupuesto(_usuario_actual(), datos["id_proyecto"], lineas, _validar_aiu(datos))
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


@bp.post("/<int:id>/partidas")
def agregar_partida_catalogo(id):
    """Agrega una partida usando el precio vigente del catálogo SQL."""
    datos = pedir(("codigo", "cantidad"))
    lineas_mano_obra = datos.get("lineas_mano_obra", [])
    if not isinstance(lineas_mano_obra, list) or any(
        not isinstance(linea, dict) or not linea.get("id_insumo") or linea.get("cantidad") is None
        for linea in lineas_mano_obra
    ):
        raise ErrorApi(400, "lineas_mano_obra debe ser una lista de insumos y cantidades válidas")
    resultado = agregar_partida_catalogo_presupuesto(
        id,
        _usuario_actual(),
        datos["codigo"],
        datos["cantidad"],
        variacion_id=datos.get("variacion_id"),
        lineas_mano_obra=lineas_mano_obra,
    )
    return jsonify(resultado), 201


@bp.post("/<int:id>/importar-txt/analizar")
def analizar_txt_bim(id):
    """Analiza un TXT de Revit/Archicad y propone partidas del catálogo SQL."""
    obtener_presupuesto(id, _usuario_actual())  # Valida sesión y acceso al presupuesto.
    archivo = request.files.get("archivo")
    software = (request.form.get("software") or "").strip().lower()
    if not archivo or not archivo.filename or not archivo.filename.lower().endswith(".txt"):
        raise ErrorApi(400, "Selecciona un archivo .txt exportado desde Revit o Archicad")
    return jsonify(leer_txt_bim(archivo.read(5 * 1024 * 1024 + 1), software))


@bp.post("/<int:id>/mano-obra-asociada")
def completar_mano_obra_asociada(id):
    """Completa perfiles asociados a equipos usando únicamente el catálogo SQL."""
    return jsonify(agregar_mano_obra_asociada(id, _usuario_actual()))


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
    resultado = duplicar_presupuesto(
        id, _usuario_actual(), datos.get("id_proyecto"), datos.get("nuevo_proyecto")
    )
    return jsonify(resultado), 201
