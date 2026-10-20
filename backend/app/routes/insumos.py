"""CU-01: gestión de catálogos e insumos."""
from flask import Blueprint, jsonify, request
from sqlalchemy import text

from ..database import engine
from ..errors import ErrorApi
from ..utils import en_uso, filas, numero, obtener, pedir

bp = Blueprint("insumos", __name__, url_prefix="/api/insumos")
CAMPOS = ["nombre_insumo", "unidad_medida", "costo_unitario"]


@bp.get("")
def listar():
    q = f"%{request.args.get('q', '')}%"
    ciudad = request.args.get("ciudad", "").strip()
    with engine.connect() as con:
        sql = ("SELECT i.id_insumo, i.nombre_insumo, i.unidad_medida, "
               "COALESCE(pc.costo_unitario, i.costo_unitario) AS costo_unitario, "
               "CASE WHEN pc.id_precio IS NULL THEN 'referencia_general' ELSE 'precio_ciudad' END AS origen_precio "
               "FROM INSUMOS i LEFT JOIN PRECIOS_CIUDAD pc ON pc.id_insumo=i.id_insumo AND pc.ciudad=:ciudad "
               "WHERE i.nombre_insumo LIKE :q ORDER BY i.nombre_insumo")
        return jsonify(filas(con.execute(text(sql), {"q": q, "ciudad": ciudad})))


@bp.get("/<int:id>")
def ver(id):
    with engine.connect() as con:
        return jsonify(obtener(con, "INSUMOS", "id_insumo", id))


@bp.post("")
def crear():
    d = pedir(CAMPOS)
    if not all(isinstance(d[field], str) for field in ("nombre_insumo", "unidad_medida")):
        raise ErrorApi(400, "El nombre y la unidad del insumo deben ser texto")
    costo = numero(d["costo_unitario"], "costo_unitario")
    with engine.begin() as con:
        nombre, unidad = d["nombre_insumo"].strip(), d["unidad_medida"].strip()
        if not nombre or not unidad:
            raise ErrorApi(400, "El nombre y la unidad del insumo son obligatorios")
        ciudad = d.get("ciudad")
        if ciudad:
            if not isinstance(ciudad, str) or not ciudad.strip() or len(ciudad.strip()) > 100:
                raise ErrorApi(400, "La ciudad no es válida")
            actual = con.execute(text("SELECT id_insumo FROM INSUMOS WHERE nombre_insumo=:n"), {"n": nombre}).scalar()
            if actual:
                id_insumo = actual
                unidad_actual = con.execute(text("SELECT unidad_medida FROM INSUMOS WHERE id_insumo=:i"), {"i": id_insumo}).scalar()
                if unidad_actual != unidad:
                    raise ErrorApi(409, "Ya existe un insumo con ese nombre y otra unidad")
            else:
                result = con.execute(text(
                    "INSERT INTO INSUMOS (nombre_insumo, unidad_medida, costo_unitario) VALUES (:n, :u, :c)"),
                    {"n": nombre, "u": unidad, "c": 0})
                id_insumo = result.lastrowid
            existe = con.execute(text("SELECT id_precio FROM PRECIOS_CIUDAD WHERE id_insumo=:i AND ciudad=:c"),
                                 {"i": id_insumo, "c": ciudad.strip()}).scalar()
            if existe:
                con.execute(text("UPDATE PRECIOS_CIUDAD SET costo_unitario=:p WHERE id_precio=:id"), {"p": costo, "id": existe})
            else:
                con.execute(text("INSERT INTO PRECIOS_CIUDAD (id_insumo, ciudad, costo_unitario) VALUES (:i, :c, :p)"),
                            {"i": id_insumo, "c": ciudad.strip(), "p": costo})
            result_item = obtener(con, "INSUMOS", "id_insumo", id_insumo)
            result_item["costo_unitario"] = costo
            result_item["origen_precio"] = "precio_ciudad"
            result_item["ciudad"] = ciudad.strip()
            return jsonify(result_item), 201
        r = con.execute(text(
            "INSERT INTO INSUMOS (nombre_insumo, unidad_medida, costo_unitario) VALUES (:n, :u, :c)"),
            {"n": nombre, "u": unidad, "c": costo})
        return jsonify(obtener(con, "INSUMOS", "id_insumo", r.lastrowid)), 201


@bp.put("/<int:id>")
def actualizar(id):
    d = pedir(CAMPOS)
    costo = numero(d["costo_unitario"], "costo_unitario")
    with engine.begin() as con:
        obtener(con, "INSUMOS", "id_insumo", id)
        con.execute(text(
            "UPDATE INSUMOS SET nombre_insumo=:n, unidad_medida=:u, costo_unitario=:c WHERE id_insumo=:i"),
            {"n": d["nombre_insumo"].strip(), "u": d["unidad_medida"].strip(), "c": costo, "i": id})
        return jsonify(obtener(con, "INSUMOS", "id_insumo", id))


@bp.delete("/<int:id>")
def eliminar(id):
    with engine.begin() as con:
        obtener(con, "INSUMOS", "id_insumo", id)
        if en_uso(con, "SELECT COUNT(*) FROM DETALLE_PRESUPUESTO WHERE id_insumo = :v", id):
            raise ErrorApi(409, "El insumo está en uso en algún presupuesto")
        con.execute(text("DELETE FROM INSUMOS WHERE id_insumo = :v"), {"v": id})
    return "", 204
