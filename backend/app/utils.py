"""Utilidades compartidas por las rutas."""
from decimal import Decimal
from math import isfinite

from flask import request
from sqlalchemy import text

from .errors import ErrorApi


def limpiar(v):
    if isinstance(v, Decimal):
        return float(v)
    return v.isoformat() if hasattr(v, "isoformat") else v


def filas(res):
    return [{k: limpiar(v) for k, v in r._mapping.items()} for r in res]


def una(res):
    r = res.first()
    return None if r is None else {k: limpiar(v) for k, v in r._mapping.items()}


def pedir(campos):
    datos = request.get_json(silent=True)
    if not isinstance(datos, dict):
        raise ErrorApi(400, "El cuerpo de la solicitud debe ser un objeto JSON")
    faltan = [c for c in campos if datos.get(c) in (None, "")]
    if faltan:
        raise ErrorApi(400, f"Faltan campos: {', '.join(faltan)}")
    return datos


def numero(valor, campo, minimo=0, estricto=False):
    try:
        n = float(valor)
    except (TypeError, ValueError, OverflowError):
        raise ErrorApi(400, f"'{campo}' debe ser un número")
    if not isfinite(n):
        raise ErrorApi(400, f"'{campo}' debe ser un número finito")
    if n < minimo or (estricto and n == minimo):
        raise ErrorApi(400, f"'{campo}' debe ser {'mayor que' if estricto else 'al menos'} {minimo}")
    return n


def obtener(con, tabla, col, valor):
    fila = una(con.execute(text(f"SELECT * FROM {tabla} WHERE {col} = :v"), {"v": valor}))
    if fila is None:
        raise ErrorApi(404, f"No existe {tabla.lower()} con id {valor}")
    return fila


def en_uso(con, sql, valor):
    return con.execute(text(sql), {"v": valor}).scalar() > 0
