"""Fábrica de la aplicación Flask."""
import os
from flask import Flask, jsonify, request, session
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError

from .config import CORS_ORIGIN, SECRET_KEY
from .database import engine
from .errors import register_errors
from .models import meta
from .routes import actividades_bim, auth, dashboard, insumos, presupuestos, proyectos, usuarios
from .services.actividades_bim import asegurar_indices_bim


def create_app():
    if not SECRET_KEY:
        raise RuntimeError("Configura SECRET_KEY con un valor aleatorio y privado antes de iniciar la aplicación.")
    app = Flask(__name__)
    app.secret_key = SECRET_KEY
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        # Vite local runs use HTTP; deployments must set this to 1 behind HTTPS.
        SESSION_COOKIE_SECURE=os.getenv("SESSION_COOKIE_SECURE", "0") == "1",
    )
    app.json.ensure_ascii = False
    try:
        meta.create_all(engine)  # crea tablas que falten
        if "ciudad" not in {column["name"] for column in inspect(engine).get_columns("PROYECTOS")}:
            with engine.begin() as con:
                con.execute(text("ALTER TABLE PROYECTOS ADD COLUMN ciudad VARCHAR(100)"))
                con.execute(text("UPDATE PROYECTOS SET ciudad='Bogot\u00e1' WHERE ciudad IS NULL"))
    except SQLAlchemyError as error:
        app.logger.exception("No se pudo inicializar la base de datos SQL.")
        raise RuntimeError("La base de datos SQL no est\u00e1 disponible o no pudo inicializarse.") from error
    register_errors(app)
    asegurar_indices_bim()
    for modulo in (auth, insumos, usuarios, proyectos, presupuestos, actividades_bim, dashboard):
        app.register_blueprint(modulo.bp)

    @app.before_request
    def exigir_sesion():
        if request.method == "OPTIONS":
            return None
        # SameSite=Lax alone does not prevent requests from a hostile same-site
        # subdomain. Browser writes must come from a configured frontend origin.
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            origin = request.headers.get("Origin")
            allowed_origins = {item.strip() for item in CORS_ORIGIN.split(",") if item.strip()}
            if origin and origin not in allowed_origins:
                return jsonify(error="Origen no permitido"), 403
        publico = (
            request.path == "/api/salud"
            or request.path.startswith("/api/auth/")
        )
        if publico:
            return None
        if not session.get("id_usuario"):
            if request.path.startswith("/api/"):
                return jsonify(error="Inicia sesión para continuar"), 401
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

    @app.get("/api/salud")
    def salud():
        return {"estado": "ok"}

    return app
