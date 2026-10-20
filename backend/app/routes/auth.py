"""Registro y gestion de sesiones."""
import re
from datetime import datetime, timezone

from flask import Blueprint, jsonify, session
from sqlalchemy import text
from werkzeug.security import check_password_hash, generate_password_hash

from ..database import engine
from ..errors import ErrorApi
from ..utils import pedir

bp = Blueprint("auth", __name__, url_prefix="/api/auth")
EMAIL = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
ROLES_REGISTRO = {"arquitecto", "ingeniero", "cliente"}


def _usuario(con, id_usuario):
    row = con.execute(text(
        "SELECT id_usuario, nombre_completo, email, rol FROM USUARIOS WHERE id_usuario = :id"),
        {"id": id_usuario}).mappings().first()
    return dict(row) if row else None


@bp.post("/registro")
def registrar():
    datos = pedir(["nombre_completo", "email", "password", "rol"])
    if not all(isinstance(datos[campo], str) for campo in ("nombre_completo", "email", "password", "rol")):
        raise ErrorApi(400, "Nombre, correo, contrasena y rol deben ser texto")
    nombre = datos["nombre_completo"].strip()
    email = datos["email"].strip().lower()
    password = datos["password"]
    rol = datos["rol"]
    if datos.get("autoriza_datos") is not True:
        raise ErrorApi(400, "Debes autorizar el tratamiento de datos para crear una cuenta")
    if len(nombre) < 2 or len(nombre) > 150:
        raise ErrorApi(400, "El nombre debe tener entre 2 y 150 caracteres")
    if len(email) > 150 or not EMAIL.match(email):
        raise ErrorApi(400, "Ingresa un correo valido")
    if len(password) < 10 or len(password) > 128:
        raise ErrorApi(400, "La contrasena debe tener entre 10 y 128 caracteres")
    if rol not in ROLES_REGISTRO:
        raise ErrorApi(400, "El rol debe ser arquitecto, ingeniero o cliente")

    with engine.begin() as con:
        result = con.execute(text(
            "INSERT INTO USUARIOS (nombre_completo, email, rol) VALUES (:n, :e, :r)"),
            {"n": nombre, "e": email, "r": rol})
        id_usuario = result.lastrowid
        con.execute(text(
            "INSERT INTO CREDENCIALES (id_usuario, password_hash) VALUES (:id, :hash)"),
            {"id": id_usuario, "hash": generate_password_hash(password)})
        con.execute(text(
            "INSERT INTO AUTORIZACIONES_DATOS (id_usuario, version_politica, fecha_autorizacion) "
            "VALUES (:id, :version, :fecha)"),
            {"id": id_usuario, "version": "2026-10-15", "fecha": datetime.now(timezone.utc).isoformat()})
        user = _usuario(con, id_usuario)

    session.clear()
    session["id_usuario"] = id_usuario
    return jsonify(user), 201


@bp.post("/login")
def iniciar_sesion():
    datos = pedir(["email", "password"])
    if not all(isinstance(datos[campo], str) for campo in ("email", "password")):
        raise ErrorApi(400, "Correo y contrasena deben ser texto")
    email = datos["email"].strip().lower()
    with engine.connect() as con:
        row = con.execute(text(
            "SELECT u.id_usuario, c.password_hash FROM USUARIOS u "
            "JOIN CREDENCIALES c ON c.id_usuario = u.id_usuario WHERE u.email = :email"),
            {"email": email}).mappings().first()
        if not row or not check_password_hash(row["password_hash"], datos["password"]):
            raise ErrorApi(401, "Correo o contrasena incorrectos")
        user = _usuario(con, row["id_usuario"])

    session.clear()
    session["id_usuario"] = user["id_usuario"]
    return jsonify(user)


@bp.get("/sesion")
def sesion_actual():
    id_usuario = session.get("id_usuario")
    if not id_usuario:
        raise ErrorApi(401, "Inicia sesion para continuar")
    with engine.connect() as con:
        user = _usuario(con, id_usuario)
    if not user:
        session.clear()
        raise ErrorApi(401, "La sesion ya no es valida")
    return jsonify(user)


@bp.post("/logout")
def cerrar_sesion():
    session.clear()
    return jsonify(mensaje="Sesion cerrada")


@bp.put("/perfil")
def actualizar_perfil():
    datos = pedir(["nombre_completo", "email", "current_password"])
    campos = ("nombre_completo", "email", "current_password", "new_password")
    if not all(isinstance(datos.get(campo, ""), str) for campo in campos):
        raise ErrorApi(400, "Los datos del perfil deben ser texto")
    nombre = datos["nombre_completo"].strip()
    email = datos["email"].strip().lower()
    nueva = datos.get("new_password", "")
    if len(nombre) < 2 or len(nombre) > 150:
        raise ErrorApi(400, "El nombre debe tener entre 2 y 150 caracteres")
    if len(email) > 150 or not EMAIL.match(email):
        raise ErrorApi(400, "Ingresa un correo valido")
    if nueva and not 10 <= len(nueva) <= 128:
        raise ErrorApi(400, "La nueva contrasena debe tener entre 10 y 128 caracteres")

    id_usuario = session.get("id_usuario")
    if not id_usuario:
        raise ErrorApi(401, "Inicia sesion para continuar")
    with engine.begin() as con:
        password_hash = con.execute(text(
            "SELECT password_hash FROM CREDENCIALES WHERE id_usuario = :id"),
            {"id": id_usuario}).scalar()
        if not password_hash or not check_password_hash(password_hash, datos["current_password"]):
            raise ErrorApi(400, "La contrasena actual no coincide")
        existente = con.execute(text(
            "SELECT id_usuario FROM USUARIOS WHERE email = :email AND id_usuario != :id"),
            {"email": email, "id": id_usuario}).scalar()
        if existente:
            raise ErrorApi(409, "Ese correo ya esta asociado a otra cuenta")
        con.execute(text(
            "UPDATE USUARIOS SET nombre_completo = :nombre, email = :email WHERE id_usuario = :id"),
            {"nombre": nombre, "email": email, "id": id_usuario})
        if nueva:
            con.execute(text(
                "UPDATE CREDENCIALES SET password_hash = :hash WHERE id_usuario = :id"),
                {"hash": generate_password_hash(nueva), "id": id_usuario})
        user = _usuario(con, id_usuario)
    return jsonify(user)
