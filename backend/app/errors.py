"""Errores de la API en JSON y cabeceras CORS."""
from flask import jsonify, request
from pymongo.errors import PyMongoError
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError

from .config import CORS_ORIGIN


class ErrorApi(Exception):
    def __init__(self, code, msg):
        super().__init__(msg)
        self.code, self.msg = code, msg


def register_errors(app):
    @app.errorhandler(ErrorApi)
    def _error_api(e):
        return jsonify(error=e.msg), e.code

    @app.errorhandler(IntegrityError)
    def _integridad(e):
        return jsonify(error="Operación no permitida: dato duplicado o en uso"), 409

    @app.errorhandler(OperationalError)
    def _base_datos_no_disponible(e):
        app.logger.error("La base SQL no pudo completar una operación.", exc_info=(type(e), e, e.__traceback__))
        return jsonify(error="La base de datos no está disponible temporalmente. Inténtalo de nuevo."), 503

    @app.errorhandler(SQLAlchemyError)
    def _error_sql(e):
        app.logger.error("Error al ejecutar una operación SQL.", exc_info=(type(e), e, e.__traceback__))
        return jsonify(error="No se pudo completar la operación en la base de datos."), 500

    @app.errorhandler(PyMongoError)
    def _error_mongo(e):
        app.logger.error("MongoDB no pudo completar una operación BIM.", exc_info=(type(e), e, e.__traceback__))
        return jsonify(error="El historial BIM no está disponible temporalmente. Inténtalo de nuevo."), 503

    @app.errorhandler(404)
    def _no_encontrado(e):
        return jsonify(error="Ruta no encontrada"), 404

    @app.after_request
    def _cors(resp):  # permite que Vite consuma la API con la cookie de sesiÃ³n
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Referrer-Policy", "no-referrer")
        resp.headers.setdefault("Cache-Control", "no-store")
        origin = request.headers.get("Origin")
        allowed_origins = {item.strip() for item in CORS_ORIGIN.split(",") if item.strip()}
        if origin and origin in allowed_origins:
            resp.headers["Access-Control-Allow-Origin"] = origin
            resp.headers["Access-Control-Allow-Credentials"] = "true"
            resp.vary.add("Origin")
        elif "*" in allowed_origins:
            resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
        resp.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        return resp
