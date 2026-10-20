"""Fábrica de la aplicación Flask."""
import os
from pathlib import Path

from flask import Flask, jsonify, redirect, request, send_from_directory, session
from sqlalchemy import inspect, text

from .config import SECRET_KEY
from .database import engine
from .errors import register_errors
from .models import meta
from .routes import actividades_bim, auth, insumos, presupuestos, proyectos, usuarios
from .services.actividades_bim import asegurar_indices_bim


def create_app():
    if not SECRET_KEY:
        raise RuntimeError("Configura SECRET_KEY con un valor aleatorio y privado antes de iniciar la aplicación.")
    frontend = Path(__file__).resolve().parents[2] / "frontend"
    app = Flask(__name__, static_folder=str(frontend), static_url_path="")
    app.secret_key = SECRET_KEY
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.getenv("SESSION_COOKIE_SECURE", "1") == "1",
    )
    app.json.ensure_ascii = False
    meta.create_all(engine)  # crea tablas que falten
    if "ciudad" not in {column["name"] for column in inspect(engine).get_columns("PROYECTOS")}:
        with engine.begin() as con:
            con.execute(text("ALTER TABLE PROYECTOS ADD COLUMN ciudad VARCHAR(100)"))
            con.execute(text("UPDATE PROYECTOS SET ciudad='Bogotá' WHERE ciudad IS NULL"))
    register_errors(app)
    asegurar_indices_bim()
    for modulo in (auth, insumos, usuarios, proyectos, presupuestos, actividades_bim):
        app.register_blueprint(modulo.bp)

    @app.before_request
    def exigir_sesion():
        publico = (
            request.path in ("/", "/login", "/registro", "/terminos", "/privacidad", "/contacto", "/api/salud")
            or request.path.startswith("/api/auth/")
            or request.path.startswith("/api/actividades-bim")
        )
        dashboard = request.path in ("/dashboard", "/dashboard.html", "/perfil")
        if publico:
            return None
        if not session.get("id_usuario"):
            if request.path.startswith("/api/"):
                return jsonify(error="Inicia sesión para continuar"), 401
            if dashboard:
                return redirect("/login")
        elif request.path.startswith("/api/") and request.method in ("POST", "PUT", "PATCH", "DELETE") and not request.path.startswith("/api/auth/"):
            with engine.connect() as con:
                rol = con.execute(text("SELECT rol FROM USUARIOS WHERE id_usuario = :id"),
                                  {"id": session["id_usuario"]}).scalar()
            if not rol:
                session.clear()
                return jsonify(error="La sesion ya no es valida"), 401
            if rol == "cliente":
                return jsonify(error="El perfil de cliente solo permite consultar"), 403
        if request.path.startswith("/api/usuarios") and session.get("id_usuario"):
            with engine.connect() as con:
                rol = con.execute(text("SELECT rol FROM USUARIOS WHERE id_usuario = :id"),
                                  {"id": session["id_usuario"]}).scalar()
            if rol != "administrador":
                return jsonify(error="Solo un administrador puede consultar usuarios"), 403
        return None

    @app.get("/")
    def inicio():
        return send_from_directory(frontend, "index.html")

    @app.get("/login")
    def pagina_login():
        return send_from_directory(frontend, "login.html")

    @app.get("/registro")
    def pagina_registro():
        return send_from_directory(frontend, "registro.html")

    @app.get("/dashboard")
    def pagina_dashboard():
        return send_from_directory(frontend, "dashboard.html")

    @app.get("/perfil")
    def pagina_perfil():
        return send_from_directory(frontend, "perfil.html")

    @app.get("/terminos")
    def pagina_terminos():
        return send_from_directory(frontend, "terminos.html")

    @app.get("/privacidad")
    def pagina_privacidad():
        return send_from_directory(frontend, "privacidad.html")

    @app.get("/contacto")
    def pagina_contacto():
        return send_from_directory(frontend, "contacto.html")

    @app.get("/api/salud")
    def salud():
        return {"estado": "ok"}

    return app
