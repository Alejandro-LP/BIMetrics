"""Registro central de errores HTTP y respuestas JSON de la API."""

from flask import jsonify, request
from pymongo.errors import DuplicateKeyError, PyMongoError
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError
from werkzeug.exceptions import HTTPException

from .config import CORS_ORIGIN


class ErrorApi(Exception):
    """Error controlado de dominio que debe exponerse como respuesta HTTP."""

    def __init__(self, code: int, msg: str):
        super().__init__(msg)
        self.code = code
        self.msg = msg


def register_errors(app):
    """Registra serialización JSON, logging de persistencia y cabeceras comunes."""

    @app.errorhandler(ErrorApi)
    def handle_api_error(error):
        return jsonify(error=error.msg), error.code

    @app.errorhandler(IntegrityError)
    def handle_integrity_error(error):
        app.logger.info("La operación fue rechazada por una restricción de integridad.")
        return jsonify(error="Operación no permitida: dato duplicado o en uso"), 409

    @app.errorhandler(OperationalError)
    def handle_database_unavailable(error):
        app.logger.error("La base SQL no pudo completar una operación.", exc_info=error)
        return jsonify(error="La base de datos no está disponible temporalmente. Inténtalo de nuevo."), 503

    @app.errorhandler(SQLAlchemyError)
    def handle_database_error(error):
        app.logger.error("Error al ejecutar una operación SQL.", exc_info=error)
        return jsonify(error="No se pudo completar la operación en la base de datos."), 500

    @app.errorhandler(PyMongoError)
    def handle_mongo_error(error):
        app.logger.error("MongoDB no pudo completar la operaci?n.", exc_info=error)
        return jsonify(error="MongoDB no disponible. Verifica MONGO_URI, DNS y el acceso de red al cluster."), 503

    @app.errorhandler(DuplicateKeyError)
    def handle_mongo_duplicate(error):
        return jsonify(error="Ya existe un usuario con ese correo"), 409

    @app.errorhandler(404)
    def handle_not_found(error):
        return jsonify(error="Ruta no encontrada"), 404

    @app.errorhandler(HTTPException)
    def handle_http_error(error):
        return jsonify(error=error.description or "Solicitud no válida"), error.code

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        app.logger.exception("Error interno no controlado durante una solicitud.")
        return jsonify(error="No se pudo completar la solicitud."), 500

    @app.after_request
    def apply_security_and_cors_headers(response):
        """Añade cabeceras de seguridad y CORS para orígenes configurados."""
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Cache-Control", "no-store")

        origin = request.headers.get("Origin")
        allowed_origins = {item.strip() for item in CORS_ORIGIN.split(",") if item.strip()}
        if origin and origin in allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.vary.add("Origin")
        elif "*" in allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = "*"

        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        return response
