"""Administración global de usuarios."""
from flask import Blueprint, jsonify, request, session
from sqlalchemy import text

from ..config import ROLES
from ..database import engine
from ..errors import ErrorApi
from ..utils import en_uso, filas, obtener, pedir

bp = Blueprint("usuarios", __name__, url_prefix="/api/usuarios")
CAMPOS = ["nombre_completo", "email", "rol"]


def _validar():
    d = pedir(CAMPOS)
    if d["rol"] not in ROLES:
        raise ErrorApi(400, f"'rol' debe ser uno de: {', '.join(sorted(ROLES))}")
    if d["rol"] == "administrador":
        with engine.connect() as con:
            actual = con.execute(text(
                "SELECT rol FROM USUARIOS WHERE id_usuario = :id"),
                {"id": session.get("id_usuario")}).scalar()
        if actual != "administrador":
            raise ErrorApi(403, "Solo un administrador puede asignar ese rol")
    return {"n": d["nombre_completo"].strip(), "e": d["email"].strip().lower(), "r": d["rol"]}


@bp.get("")
def listar():
    rol = request.args.get("rol")
    with engine.connect() as con:
        if rol:
            res = con.execute(text("SELECT * FROM USUARIOS WHERE rol = :r ORDER BY nombre_completo"), {"r": rol})
        else:
            res = con.execute(text("SELECT * FROM USUARIOS ORDER BY nombre_completo"))
        return jsonify(filas(res))


@bp.get("/<int:id>")
def ver(id):
    with engine.connect() as con:
        return jsonify(obtener(con, "USUARIOS", "id_usuario", id))


@bp.post("")
def crear():
    p = _validar()
    with engine.begin() as con:
        r = con.execute(text("INSERT INTO USUARIOS (nombre_completo, email, rol) VALUES (:n, :e, :r)"), p)
        return jsonify(obtener(con, "USUARIOS", "id_usuario", r.lastrowid)), 201


@bp.put("/<int:id>")
def actualizar(id):
    p = _validar()
    with engine.begin() as con:
        obtener(con, "USUARIOS", "id_usuario", id)
        con.execute(text(
            "UPDATE USUARIOS SET nombre_completo=:n, email=:e, rol=:r WHERE id_usuario=:i"), {**p, "i": id})
        return jsonify(obtener(con, "USUARIOS", "id_usuario", id))


@bp.delete("/<int:id>")
def eliminar(id):
    with engine.begin() as con:
        obtener(con, "USUARIOS", "id_usuario", id)
        if en_uso(con, "SELECT COUNT(*) FROM PROYECTOS WHERE id_usuario = :v", id):
            raise ErrorApi(409, "El usuario tiene proyectos asociados")
        con.execute(text("DELETE FROM AUTORIZACIONES_DATOS WHERE id_usuario = :v"), {"v": id})
        con.execute(text("DELETE FROM CREDENCIALES WHERE id_usuario = :v"), {"v": id})
        con.execute(text("DELETE FROM USUARIOS WHERE id_usuario = :v"), {"v": id})
    return "", 204
