"""Fábrica de la aplicación Flask."""
import os
from flask import Flask, jsonify, request, session
from pymongo.errors import PyMongoError
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError

from .config import (
    CATALOG_DATABASE_URL,
    CORS_ORIGIN,
    MONGO_ACTIVITY_DB_NAME,
    MONGO_DNS_SERVERS,
    MONGO_DB_NAME,
    MONGO_URI,
    SECRET_KEY,
)
from .database import get_mongo_db, init_mongo, operational_engine
from .errors import register_errors
from .models import meta
from .extensions import db
from . import catalog_models  # noqa: F401  # Registra las entidades del catálogo en Flask-SQLAlchemy.
from .routes import actividades_bim, auth, dashboard, insumos, partidas_routes, presupuestos, proyectos, usuarios
from .services.actividades_bim import asegurar_indices_bim
from .services.usuarios_mongo import asegurar_indices_usuarios, obtener_usuario


def create_app():
    """Crea y configura una instancia Flask con sus dependencias y rutas."""
    if not SECRET_KEY:
        raise RuntimeError("Configura SECRET_KEY con un valor aleatorio y privado antes de iniciar la aplicación.")
    app = Flask(__name__)
    app.secret_key = SECRET_KEY
    app.config.update(
        SQLALCHEMY_DATABASE_URI=CATALOG_DATABASE_URL,
        SQLALCHEMY_ENGINE_OPTIONS={"pool_pre_ping": True},
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        MONGO_URI=MONGO_URI,
        MONGO_DNS_SERVERS=MONGO_DNS_SERVERS,
        MONGO_USERS_DB=MONGO_DB_NAME,
        MONGO_ACTIVITY_DB=MONGO_ACTIVITY_DB_NAME,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        # Vite local runs use HTTP; deployments must set this to 1 behind HTTPS.
        SESSION_COOKIE_SECURE=os.getenv("SESSION_COOKIE_SECURE", "0") == "1",
    )
    app.json.ensure_ascii = False
    db.init_app(app)
    init_mongo(app)
    try:
        meta.create_all(operational_engine)
        if "ciudad" not in {column["name"] for column in inspect(operational_engine).get_columns("PROYECTOS")}:
            with operational_engine.begin() as con:
                con.execute(text("ALTER TABLE PROYECTOS ADD COLUMN ciudad VARCHAR(100)"))
                con.execute(text("UPDATE PROYECTOS SET ciudad='Bogot\u00e1' WHERE ciudad IS NULL"))
        with app.app_context():
            db.create_all()
    except SQLAlchemyError as error:
        app.logger.exception("No se pudo inicializar una de las bases SQL.")
        raise RuntimeError("No se pudo inicializar la base de datos del catálogo u operacional.") from error
    register_errors(app)
    with app.app_context():
        asegurar_indices_usuarios()
        asegurar_indices_bim()
    for modulo in (auth, insumos, usuarios, proyectos, presupuestos, partidas_routes, actividades_bim, dashboard):
        app.register_blueprint(modulo.bp)

    @app.before_request
    def exigir_sesion():
        """Aplica controles de origen, sesión y permisos antes de la API."""
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
            or request.path == "/api/salud/mongodb"
            or request.path.startswith("/api/auth/")
        )
        if publico:
            return None
        if not session.get("id_usuario"):
            if request.path.startswith("/api/"):
                return jsonify(error="Inicia sesión para continuar"), 401
        elif request.path.startswith("/api/") and request.method in ("POST", "PUT", "PATCH", "DELETE") and not request.path.startswith("/api/auth/"):
            usuario = obtener_usuario(session["id_usuario"])
            if not usuario:
                session.clear()
                return jsonify(error="La sesión ya no es válida"), 401
            if usuario["rol"] == "cliente":
                return jsonify(error="El perfil de cliente solo permite consultar"), 403
        if request.path.startswith("/api/usuarios") and session.get("id_usuario"):
            usuario = obtener_usuario(session["id_usuario"])
            if not usuario or usuario["rol"] != "administrador":
                return jsonify(error="Solo un administrador puede consultar usuarios"), 403
        return None

    @app.get("/api/salud")
    def salud():
        return {"estado": "ok"}

    @app.get("/api/salud/mongodb")
    def salud_mongodb():
        """Comprueba la conectividad Mongo sin exponer URI ni datos."""
        try:
            get_mongo_db("users").command("ping")
        except PyMongoError:
            # Keep API responses generic, but expose the root cause in the
            # backend console so connection failures can be diagnosed locally.
            app.logger.exception("No se pudo conectar con MongoDB en /api/salud/mongodb.")
            return jsonify(estado="no_disponible", servicio="mongodb"), 503
        return jsonify(estado="ok", servicio="mongodb")

    return app
