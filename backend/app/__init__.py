"""Fábrica de la aplicación Flask."""
import os
from flask import Flask, jsonify, request, session
from pymongo.errors import PyMongoError
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError

from .config import (
    APP_BASE_URL,
    CATALOG_DATABASE_URL,
    CORS_ORIGIN,
    PASSWORD_RESET_DEBUG,
    MONGO_ACTIVITY_DB_NAME,
    MONGO_DNS_SERVERS,
    MONGO_DB_NAME,
    MONGO_URI,
    SECRET_KEY,
    SMTP_FROM,
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_USE_TLS,
    SMTP_USERNAME,
)
from .database import get_mongo_db, init_mongo, operational_engine
from .errors import register_errors
from .models import meta
from .extensions import db
from . import catalog_models  # noqa: F401  # Registra las entidades del catálogo en Flask-SQLAlchemy.
from .routes import actividades_bim, auth, dashboard, insumos, partidas_routes, presupuestos, proyectos, usuarios
from .services.actividades_bim import asegurar_indices_bim
from .services.usuarios_mongo import asegurar_indices_usuarios, obtener_documento_usuario, obtener_usuario


def create_app():
    """Crea y configura una instancia Flask con sus dependencias y rutas."""
    if not SECRET_KEY:
        raise RuntimeError("Configura SECRET_KEY con un valor aleatorio y privado antes de iniciar la aplicación.")
    app = Flask(__name__)
    app.secret_key = SECRET_KEY
    session_cookie_secure = os.getenv("SESSION_COOKIE_SECURE", "0") == "1"
    production = os.getenv("BIMETRICS_ENV", "development").strip().lower() == "production"
    if production and not session_cookie_secure:
        raise RuntimeError("En producción configura SESSION_COOKIE_SECURE=1 y sirve la aplicación mediante HTTPS.")
    if production and len(SECRET_KEY) < 32:
        raise RuntimeError("En producción SECRET_KEY debe tener al menos 32 caracteres aleatorios.")
    app.config.update(
        SQLALCHEMY_DATABASE_URI=CATALOG_DATABASE_URL,
        SQLALCHEMY_ENGINE_OPTIONS={"pool_pre_ping": True},
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        # Cota global de solicitudes; permite archivos TXT de hasta 5 MB más multipart.
        MAX_CONTENT_LENGTH=6 * 1024 * 1024,
        MONGO_URI=MONGO_URI,
        MONGO_DNS_SERVERS=MONGO_DNS_SERVERS,
        MONGO_USERS_DB=MONGO_DB_NAME,
        MONGO_ACTIVITY_DB=MONGO_ACTIVITY_DB_NAME,
        APP_BASE_URL=APP_BASE_URL,
        BIMETRICS_ENV=os.getenv("BIMETRICS_ENV", "development").strip().lower(),
        PASSWORD_RESET_DEBUG=PASSWORD_RESET_DEBUG,
        SMTP_HOST=SMTP_HOST,
        SMTP_PORT=SMTP_PORT,
        SMTP_USERNAME=SMTP_USERNAME,
        SMTP_PASSWORD=SMTP_PASSWORD,
        SMTP_FROM=SMTP_FROM,
        SMTP_USE_TLS=SMTP_USE_TLS,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        # Vite local runs use HTTP; deployments must set this to 1 behind HTTPS.
        SESSION_COOKIE_SECURE=session_cookie_secure,
    )
    app.json.ensure_ascii = False
    db.init_app(app)
    init_mongo(app)
    try:
        meta.create_all(operational_engine)
        columnas_presupuesto = {column["name"] for column in inspect(operational_engine).get_columns("PRESUPUESTOS")}
        columnas_detalle = {column["name"] for column in inspect(operational_engine).get_columns("DETALLE_PRESUPUESTO")}
        columnas_insumos = {column["name"] for column in inspect(operational_engine).get_columns("INSUMOS")}
        columnas_aiu = {
            "porcentaje_administracion": "NUMERIC(5, 2) NOT NULL DEFAULT 0",
            "porcentaje_imprevistos": "NUMERIC(5, 2) NOT NULL DEFAULT 0",
            "porcentaje_utilidad": "NUMERIC(5, 2) NOT NULL DEFAULT 0",
        }
        with operational_engine.begin() as con:
            if "capitulo" not in columnas_detalle:
                con.execute(text("ALTER TABLE DETALLE_PRESUPUESTO ADD COLUMN capitulo VARCHAR(100)"))
            if "activo" not in columnas_insumos:
                con.execute(text("ALTER TABLE INSUMOS ADD COLUMN activo BOOLEAN NOT NULL DEFAULT 1"))
            for columna, tipo in columnas_aiu.items():
                if columna not in columnas_presupuesto:
                    con.execute(text(f"ALTER TABLE PRESUPUESTOS ADD COLUMN {columna} {tipo}"))
        if "ciudad" not in {column["name"] for column in inspect(operational_engine).get_columns("PROYECTOS")}:
            with operational_engine.begin() as con:
                con.execute(text("ALTER TABLE PROYECTOS ADD COLUMN ciudad VARCHAR(100)"))
                con.execute(text("UPDATE PROYECTOS SET ciudad='Bogot\u00e1' WHERE ciudad IS NULL"))
        with app.app_context():
            db.create_all()
            columnas_recomendaciones = {
                columna["name"]
                for columna in inspect(db.engine).get_columns("recomendaciones_mano_obra")
            }
            if "rendimiento_por_jornal" not in columnas_recomendaciones:
                with db.engine.begin() as con:
                    con.execute(text(
                        "ALTER TABLE recomendaciones_mano_obra "
                        "ADD COLUMN rendimiento_por_jornal DECIMAL(12, 6) NULL"
                    ))
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
            if not origin or origin not in allowed_origins:
                return jsonify(error="Origen no permitido"), 403
        publico = (
            request.path == "/api/salud"
            or request.path == "/api/salud/sql"
            or request.path == "/api/salud/mongodb"
            or request.path in {
                "/api/auth/registro",
                "/api/auth/login",
                "/api/auth/logout",
                "/api/auth/solicitar-restablecimiento",
                "/api/auth/restablecer-password",
            }
        )
        if publico:
            return None
        if not session.get("id_usuario"):
            if request.path.startswith("/api/"):
                return jsonify(error="Inicia sesión para continuar"), 401
        elif request.path.startswith("/api/"):
            documento_sesion = obtener_documento_usuario(session["id_usuario"])
            version_actual = int(documento_sesion.get("version_sesion", 1)) if documento_sesion else None
            if version_actual is None or session.get("version_sesion") != version_actual:
                session.clear()
                return jsonify(error="La sesión expiró. Inicia sesión nuevamente."), 401
        if session.get("id_usuario") and request.path.startswith("/api/") and request.method in ("POST", "PUT", "PATCH", "DELETE") and not request.path.startswith("/api/auth/"):
            usuario = obtener_usuario(session["id_usuario"])
            if not usuario:
                session.clear()
                return jsonify(error="La sesión ya no es válida"), 401
            if usuario["rol"] == "cliente" and request.path != "/api/proyectos/invitaciones/aceptar":
                return jsonify(error="El perfil de cliente solo permite consultar"), 403
        if request.path.startswith("/api/usuarios") and session.get("id_usuario"):
            usuario = obtener_usuario(session["id_usuario"])
            if not usuario or usuario["rol"] != "administrador":
                return jsonify(error="Solo un administrador puede consultar usuarios"), 403
        return None

    @app.get("/api/salud")
    def salud():
        return {"estado": "ok"}

    @app.get("/api/salud/sql")
    def salud_sql():
        """Comprueba la conexión y el contenido del catálogo relacional SQL."""
        try:
            partidas = db.session.execute(text("SELECT COUNT(*) FROM partidas")).scalar_one()
            variaciones = db.session.execute(text("SELECT COUNT(*) FROM variaciones_opciones")).scalar_one()
        except SQLAlchemyError:
            db.session.rollback()
            app.logger.exception("No se pudo consultar el catálogo SQL en /api/salud/sql.")
            return jsonify(estado="no_disponible", servicio="sql_catalogo"), 503
        return jsonify(
            estado="ok",
            servicio="sql_catalogo",
            partidas=partidas,
            variaciones=variaciones,
        )

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
