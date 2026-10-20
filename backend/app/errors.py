"""Errores de la API en JSON y cabeceras CORS."""
from flask import jsonify
from sqlalchemy.exc import IntegrityError

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

    @app.errorhandler(404)
    def _no_encontrado(e):
        return jsonify(error="Ruta no encontrada"), 404

    @app.after_request
    def _cors(resp):  # permite que el dashboard consuma la API
        resp.headers["Access-Control-Allow-Origin"] = CORS_ORIGIN
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
        resp.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        return resp
