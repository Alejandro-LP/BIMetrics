"""CU-02 y CU-04: cálculo paramétrico, duplicado y reutilización de presupuestos."""
from datetime import date

from flask import Blueprint, jsonify, request, session
from sqlalchemy import text

from ..database import engine
from ..errors import ErrorApi
from ..services.presupuestos import agregar_linea, presupuesto_completo, recalcular
from ..utils import filas, obtener, pedir

bp = Blueprint("presupuestos", __name__, url_prefix="/api/presupuestos")

def _proyecto_del_usuario(con, id_proyecto):
    row = con.execute(text("SELECT id_proyecto FROM PROYECTOS y WHERE id_proyecto=:p AND "
                           "(id_usuario=:u OR EXISTS (SELECT 1 FROM PROYECTO_COLABORADORES c "
                           "WHERE c.id_proyecto=y.id_proyecto AND c.id_usuario=:u))"),
                      {"p": id_proyecto, "u": session.get("id_usuario")}).first()
    if not row:
        raise ErrorApi(404, "El proyecto no existe")

def _presupuesto_del_usuario(con, id_presupuesto):
    row = con.execute(text("SELECT p.id_presupuesto, p.id_proyecto FROM PRESUPUESTOS p JOIN PROYECTOS y "
                           "ON y.id_proyecto=p.id_proyecto WHERE p.id_presupuesto=:p AND "
                           "(y.id_usuario=:u OR EXISTS (SELECT 1 FROM PROYECTO_COLABORADORES c "
                           "WHERE c.id_proyecto=y.id_proyecto AND c.id_usuario=:u))"),
                      {"p": id_presupuesto, "u": session.get("id_usuario")}).mappings().first()
    if not row:
        raise ErrorApi(404, "El presupuesto no existe")
    return row


def _nuevo(con, id_proyecto):
    r = con.execute(text(
        "INSERT INTO PRESUPUESTOS (id_proyecto, fecha_calculo, costo_total) VALUES (:p, :f, 0)"),
        {"p": id_proyecto, "f": date.today().isoformat()})
    return r.lastrowid


@bp.get("")
def listar():
    sql = ("SELECT p.*, y.nombre_obra, y.ciudad FROM PRESUPUESTOS p "
           "JOIN PROYECTOS y ON y.id_proyecto = p.id_proyecto WHERE "
           "(y.id_usuario=:u OR EXISTS (SELECT 1 FROM PROYECTO_COLABORADORES c "
           "WHERE c.id_proyecto=y.id_proyecto AND c.id_usuario=:u))")
    pid = request.args.get("id_proyecto")
    with engine.connect() as con:
        if pid:
            res = con.execute(text(sql + " AND p.id_proyecto = :p ORDER BY p.fecha_calculo DESC"), {"p": pid, "u": session.get("id_usuario")})
        else:
            res = con.execute(text(sql + " ORDER BY p.fecha_calculo DESC, p.id_presupuesto DESC"), {"u": session.get("id_usuario")})
        return jsonify(filas(res))


@bp.get("/<int:id>")
def ver(id):
    with engine.connect() as con:
        _presupuesto_del_usuario(con, id)
        return jsonify(presupuesto_completo(con, id))


@bp.post("")
def crear():
    d = pedir(["id_proyecto"])  # opcional: "detalle": [{"id_insumo": 1, "cantidad": 2.5}, ...]
    with engine.begin() as con:
        _proyecto_del_usuario(con, d["id_proyecto"])
        nuevo = _nuevo(con, d["id_proyecto"])
        ciudad = con.execute(text("SELECT ciudad FROM PROYECTOS WHERE id_proyecto=:p"),
                             {"p": d["id_proyecto"]}).scalar()
        for linea in d.get("detalle") or []:
            agregar_linea(con, nuevo, linea.get("id_insumo"), linea.get("cantidad"), ciudad)
        recalcular(con, nuevo)
        return jsonify(presupuesto_completo(con, nuevo)), 201


@bp.post("/<int:id>/detalle")
def agregar_detalle(id):
    d = pedir(["id_insumo", "cantidad"])
    with engine.begin() as con:
        presupuesto = _presupuesto_del_usuario(con, id)
        ciudad = con.execute(text("SELECT ciudad FROM PROYECTOS WHERE id_proyecto=:p"),
                             {"p": presupuesto["id_proyecto"]}).scalar()
        agregar_linea(con, id, d["id_insumo"], d["cantidad"], ciudad)
        recalcular(con, id)
        return jsonify(presupuesto_completo(con, id)), 201


@bp.delete("/<int:id>/detalle/<int:id_detalle>")
def quitar_detalle(id, id_detalle):
    with engine.begin() as con:
        _presupuesto_del_usuario(con, id)
        res = con.execute(text(
            "DELETE FROM DETALLE_PRESUPUESTO WHERE id_detalle = :d AND id_presupuesto = :p"),
            {"d": id_detalle, "p": id})
        if res.rowcount == 0:
            raise ErrorApi(404, f"El presupuesto {id} no tiene la línea {id_detalle}")
        recalcular(con, id)
        return jsonify(presupuesto_completo(con, id))


@bp.post("/<int:id>/calcular")
def calcular(id):
    with engine.begin() as con:
        _presupuesto_del_usuario(con, id)
        return jsonify(id_presupuesto=id, costo_total=recalcular(con, id))


@bp.post("/<int:id>/duplicar")
def duplicar(id):
    d = request.get_json(silent=True) or {}  # opcional: {"id_proyecto": otro}
    with engine.begin() as con:
        original = _presupuesto_del_usuario(con, id)
        destino = d.get("id_proyecto", original["id_proyecto"])
        _proyecto_del_usuario(con, destino)
        nuevo = _nuevo(con, destino)
        con.execute(text(  # reutiliza cantidades con los costos vigentes del catálogo
            "INSERT INTO DETALLE_PRESUPUESTO (id_presupuesto, id_insumo, cantidad, costo_unitario_aplicado) "
            "SELECT :nuevo, d.id_insumo, d.cantidad, COALESCE(pc.costo_unitario, NULLIF(i.costo_unitario, 0), d.costo_unitario_aplicado) "
            "FROM DETALLE_PRESUPUESTO d JOIN INSUMOS i ON i.id_insumo=d.id_insumo "
            "JOIN PROYECTOS y ON y.id_proyecto=:destino "
            "LEFT JOIN PRECIOS_CIUDAD pc ON pc.id_insumo=i.id_insumo AND pc.ciudad=y.ciudad "
            "WHERE d.id_presupuesto=:orig"),
            {"nuevo": nuevo, "orig": id, "destino": destino})
        recalcular(con, nuevo)
        return jsonify(presupuesto_completo(con, nuevo)), 201
