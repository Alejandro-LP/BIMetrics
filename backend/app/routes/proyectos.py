"""Proyectos e historial de presupuestos (CU-04)."""
from flask import Blueprint, jsonify, session
from sqlalchemy import text

from ..database import engine
from ..errors import ErrorApi
from ..utils import filas, obtener, pedir

bp = Blueprint("proyectos", __name__, url_prefix="/api/proyectos")


@bp.get("")
def listar():
    id_usuario = session.get("id_usuario")
    if not id_usuario:
        raise ErrorApi(401, "Inicia sesion para continuar")
    with engine.connect() as con:
        return jsonify(filas(con.execute(text(
            "SELECT y.*, u.nombre_completo AS responsable, CASE WHEN y.id_usuario=:id THEN 1 ELSE 0 END AS es_propietario FROM PROYECTOS y "
            "JOIN USUARIOS u ON u.id_usuario = y.id_usuario "
            "WHERE y.id_usuario = :id OR EXISTS (SELECT 1 FROM PROYECTO_COLABORADORES c "
            "WHERE c.id_proyecto=y.id_proyecto AND c.id_usuario=:id) ORDER BY y.nombre_obra"), {"id": id_usuario})))


@bp.post("")
def crear():
    d = pedir(["nombre_obra"])
    ciudad = d.get("ciudad", "Bogotá")
    id_usuario = session.get("id_usuario")
    if not id_usuario:
        raise ErrorApi(401, "Inicia sesion para continuar")
    if not isinstance(d["nombre_obra"], str) or not d["nombre_obra"].strip():
        raise ErrorApi(400, "El nombre de la obra es obligatorio")
    if not isinstance(ciudad, str) or not ciudad.strip():
        raise ErrorApi(400, "Selecciona la ciudad del proyecto")
    with engine.begin() as con:
        r = con.execute(text(
            "INSERT INTO PROYECTOS (id_usuario, nombre_obra, cliente, ciudad) VALUES (:u, :o, :c, :ciudad)"),
            {"u": id_usuario, "o": d["nombre_obra"].strip(), "c": d.get("cliente"), "ciudad": ciudad.strip()})
        return jsonify(obtener(con, "PROYECTOS", "id_proyecto", r.lastrowid)), 201


@bp.get("/<int:id>/presupuestos")
def historial(id):
    with engine.connect() as con:
        existe = con.execute(text("SELECT 1 FROM PROYECTOS y WHERE y.id_proyecto=:p AND "
                                  "(y.id_usuario=:u OR EXISTS (SELECT 1 FROM PROYECTO_COLABORADORES c "
                                  "WHERE c.id_proyecto=y.id_proyecto AND c.id_usuario=:u))"),
                             {"p": id, "u": session.get("id_usuario")}).first()
        if not existe:
            raise ErrorApi(404, "El proyecto no existe")
        return jsonify(filas(con.execute(text(
            "SELECT * FROM PRESUPUESTOS WHERE id_proyecto = :p ORDER BY fecha_calculo DESC, id_presupuesto DESC"),
            {"p": id})))


@bp.post("/<int:id>/colaboradores")
def invitar_colaborador(id):
    d = pedir(["email"])
    email = d["email"].strip().lower() if isinstance(d["email"], str) else ""
    if not email:
        raise ErrorApi(400, "Escribe el correo de la persona colaboradora")
    id_usuario = session.get("id_usuario")
    with engine.begin() as con:
        proyecto = con.execute(text("SELECT id_proyecto FROM PROYECTOS WHERE id_proyecto=:p AND id_usuario=:u"),
                               {"p": id, "u": id_usuario}).first()
        if not proyecto:
            raise ErrorApi(404, "El proyecto no existe o no eres su propietario")
        usuario = con.execute(text("SELECT id_usuario, rol FROM USUARIOS WHERE lower(email)=:email"),
                              {"email": email}).mappings().first()
        if not usuario:
            raise ErrorApi(404, "No hay una cuenta registrada con ese correo")
        if usuario["rol"] not in ("arquitecto", "ingeniero"):
            raise ErrorApi(400, "Solo se puede invitar a un arquitecto o ingeniero")
        if usuario["id_usuario"] == id_usuario:
            raise ErrorApi(400, "Ya eres propietario de este proyecto")
        existente = con.execute(text("SELECT 1 FROM PROYECTO_COLABORADORES WHERE id_proyecto=:p AND id_usuario=:u"),
                                {"p": id, "u": usuario["id_usuario"]}).first()
        if not existente:
            con.execute(text("INSERT INTO PROYECTO_COLABORADORES (id_proyecto,id_usuario,invitado_por) "
                             "VALUES (:p,:u,:i)"), {"p": id, "u": usuario["id_usuario"], "i": id_usuario})
    return jsonify(ok=True, mensaje="Colaborador agregado al proyecto"), 201


@bp.delete("/<int:id>")
def eliminar(id):
    id_usuario = session.get("id_usuario")
    with engine.begin() as con:
        proyecto = con.execute(text(
            "SELECT id_proyecto FROM PROYECTOS WHERE id_proyecto=:p AND id_usuario=:u"),
            {"p": id, "u": id_usuario}).first()
        if not proyecto:
            raise ErrorApi(404, "El proyecto no existe")
        con.execute(text(
            "DELETE FROM DETALLE_PRESUPUESTO WHERE id_presupuesto IN "
            "(SELECT id_presupuesto FROM PRESUPUESTOS WHERE id_proyecto=:p)"), {"p": id})
        con.execute(text("DELETE FROM PRESUPUESTOS WHERE id_proyecto=:p"), {"p": id})
        con.execute(text("DELETE FROM PROYECTO_COLABORADORES WHERE id_proyecto=:p"), {"p": id})
        con.execute(text("DELETE FROM PROYECTOS WHERE id_proyecto=:p AND id_usuario=:u"),
                    {"p": id, "u": id_usuario})
    return "", 204
