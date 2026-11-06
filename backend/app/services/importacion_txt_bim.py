"""Lectura segura de cómputos TXT exportados desde Revit o Archicad."""

import csv
import math
import re
import unicodedata
from difflib import SequenceMatcher
from decimal import Decimal, InvalidOperation

from sqlalchemy import or_, select

from ..catalog_models import Partida
from ..errors import ErrorApi
from ..extensions import db

MAX_FILAS = 1000
ALIAS_NOMBRE = {
    "element", "elemento", "name", "nombre", "description", "descripcion",
    "family and type", "family type", "element name", "nombre elemento", "tipo", "type",
    "component", "componente", "item", "partida",
}
ALIAS_CANTIDAD = {"quantity", "qty", "cantidad", "unidades", "total quantity", "total qty", "measured quantity"}
ALIAS_CONTEO = {"count", "element count", "conteo", "numero de elementos", "number of elements"}
ALIAS_UNIDAD = {"unit", "units", "unidad", "unidades de medida", "uom"}
ALIAS_CODIGO = {"code", "codigo", "item code", "codigo de partida", "partida code"}
ALIAS_MEDIDAS = {"length": "m", "longitud": "m", "area": "m²", "area m2": "m²", "volume": "m³", "volumen": "m³"}
STOPWORDS = {"con", "para", "por", "del", "las", "los", "una", "uno", "and", "the", "with", "from", "element", "elemento"}


def _normalizar(texto):
    texto = unicodedata.normalize("NFKD", str(texto or "").casefold())
    texto = "".join(caracter for caracter in texto if not unicodedata.combining(caracter))
    return re.sub(r"[^a-z0-9]+", " ", texto).strip()


def _decodificar(contenido):
    for encoding in ("utf-8-sig", "utf-16", "cp1252"):
        try:
            texto = contenido.decode(encoding)
            if "\ufffd" not in texto:
                return texto
        except UnicodeDecodeError:
            continue
    raise ErrorApi(400, "No se pudo leer la codificación del TXT. Expórtalo como UTF-8, UTF-16 o Windows-1252.")


def _delimitador(lineas):
    muestra = [linea for linea in lineas[:25] if linea.strip()]
    puntuaciones = {"\t": 0, ";": 0, "|": 0, ",": 0}
    for linea in muestra:
        for delimitador in puntuaciones:
            puntuaciones[delimitador] += linea.count(delimitador)
    return max(puntuaciones, key=puntuaciones.get)


def _indice_encabezado(celdas, alias):
    """Acepta encabezados con unidad añadida, como Quantity [m²]."""
    return next(
        (indice for indice, celda in enumerate(celdas)
         if any(celda == nombre or celda.startswith(nombre + " ") for nombre in alias)),
        None,
    )


def _cantidad(valor):
    texto = re.sub(r"[^0-9,().+\-]", "", str(valor or "").strip())
    if not texto or texto in {"-", "+", ".", ","}:
        return None
    negativo = texto.startswith("(") and texto.endswith(")")
    texto = texto.strip("()")
    if "," in texto and "." in texto:
        if texto.rfind(",") > texto.rfind("."):
            texto = texto.replace(".", "").replace(",", ".")
        else:
            texto = texto.replace(",", "")
    elif "," in texto:
        partes = texto.split(",")
        texto = "".join(partes) if len(partes[-1]) == 3 and len(partes) > 1 else ".".join(partes)
    elif texto.count(".") > 1:
        partes = texto.split(".")
        texto = "".join(partes) if len(partes[-1]) == 3 else ".".join(partes[:-1]) + "." + partes[-1]
    try:
        resultado = Decimal(texto)
    except InvalidOperation:
        return None
    if negativo:
        resultado = -resultado
    if not resultado.is_finite() or resultado <= 0:
        return None
    return float(resultado)


def _sugerir_partidas(nombre, codigo=None):
    """Devuelve candidatos, sin convertir coincidencias difusas en precios."""
    if codigo:
        exacta = db.session.get(Partida, codigo.strip())
        if exacta:
            return [_serializar_candidato(exacta)]

    tokens = [token for token in _normalizar(nombre).split() if len(token) >= 4 and token not in STOPWORDS]
    if not tokens:
        return []
    condiciones = [Partida.descripcion.ilike(f"%{token}%") for token in tokens[:5]]
    candidatos = db.session.scalars(
        select(Partida).where(or_(*condiciones)).limit(100)
    ).all()
    consulta_norm = _normalizar(nombre)
    consulta_tokens = set(tokens)

    def puntuacion(partida):
        descripcion = _normalizar(partida.descripcion)
        tokens_partida = set(descripcion.split())
        cobertura = len(consulta_tokens & tokens_partida) / len(consulta_tokens)
        similitud = SequenceMatcher(None, consulta_norm, descripcion).ratio()
        return cobertura * 0.75 + similitud * 0.25

    mejores = sorted(candidatos, key=puntuacion, reverse=True)[:3]
    return [_serializar_candidato(item) for item in mejores if puntuacion(item) >= 0.12]


def _serializar_candidato(partida):
    return {
        "codigo": partida.codigo,
        "descripcion": partida.descripcion,
        "unidad": partida.unidad,
        "precio_defecto": float(partida.precio_defecto or 0),
    }


def leer_txt_bim(contenido, software):
    """Convierte una tabla de cómputos a líneas normalizadas y sugiere partidas SQL."""
    if not isinstance(contenido, bytes) or not contenido:
        raise ErrorApi(400, "El archivo TXT está vacío")
    if len(contenido) > 5 * 1024 * 1024:
        raise ErrorApi(413, "El archivo TXT supera el máximo permitido de 5 MB")
    if software not in {"revit", "archicad"}:
        raise ErrorApi(400, "software debe ser revit o archicad")

    texto = _decodificar(contenido).replace("\x00", "")
    lineas = texto.splitlines()
    delimitador = _delimitador(lineas)
    if not delimitador or max((linea.count(delimitador) for linea in lineas[:25]), default=0) == 0:
        raise ErrorApi(400, "No se detectó una tabla delimitada. Exporta la planificación de Revit o Archicad como texto tabulado.")

    filas = list(csv.reader(lineas, delimiter=delimitador, quotechar='"'))
    encabezado = None
    indices = None
    for indice_fila, fila in enumerate(filas[:40]):
        celdas = [_normalizar(celda) for celda in fila]
        nombre_idx = _indice_encabezado(celdas, ALIAS_NOMBRE)
        cantidad_idx = _indice_encabezado(celdas, ALIAS_CANTIDAD)
        if cantidad_idx is None:
            cantidad_idx = _indice_encabezado(celdas, ALIAS_CONTEO)
        unidad_idx = _indice_encabezado(celdas, ALIAS_UNIDAD)
        codigo_idx = _indice_encabezado(celdas, ALIAS_CODIGO)
        medida_idx = next(
            (i for i, celda in enumerate(celdas)
             if any(celda == nombre or celda.startswith(nombre + " ") for nombre in ALIAS_MEDIDAS)),
            None,
        )
        if cantidad_idx is None and medida_idx is not None:
            cantidad_idx = medida_idx
            encabezado_medida = _normalizar(fila[medida_idx])
            unidad_medida = next(
                valor for nombre, valor in ALIAS_MEDIDAS.items()
                if encabezado_medida == nombre or encabezado_medida.startswith(nombre + " ")
            )
        else:
            unidad_medida = None
        if nombre_idx is not None and cantidad_idx is not None:
            encabezado = indice_fila
            indices = (nombre_idx, cantidad_idx, unidad_idx, codigo_idx, unidad_medida)
            break
    if encabezado is None:
        raise ErrorApi(400, "No encontré encabezados de elemento y cantidad. Exporta una tabla con columnas Nombre/Description y Cantidad/Quantity o Count.")

    nombre_idx, cantidad_idx, unidad_idx, codigo_idx, unidad_medida_default = indices
    resultado = []
    for numero_fila, fila in enumerate(filas[encabezado + 1:], start=encabezado + 2):
        if len(fila) <= max(nombre_idx, cantidad_idx):
            continue
        nombre = str(fila[nombre_idx]).strip()
        if not nombre or _normalizar(nombre) in {"total", "subtotal", "grand total", "total general"}:
            continue
        cantidad = _cantidad(fila[cantidad_idx])
        if cantidad is None:
            continue
        unidad = str(fila[unidad_idx]).strip() if unidad_idx is not None and unidad_idx < len(fila) else ""
        unidad = unidad or unidad_medida_default or ""
        codigo = str(fila[codigo_idx]).strip() if codigo_idx is not None and codigo_idx < len(fila) else None
        if not codigo:
            codigo = None
        resultado.append({
            "indice": len(resultado),
            "linea_archivo": numero_fila,
            "nombre": nombre[:255],
            "codigo_origen": codigo,
            "cantidad": cantidad,
            "unidad": unidad[:50],
            "sugerencias": _sugerir_partidas(nombre, codigo),
        })
        if len(resultado) > MAX_FILAS:
            raise ErrorApi(413, f"El TXT supera el máximo de {MAX_FILAS} filas de elementos por importación")

    if not resultado:
        raise ErrorApi(400, "La tabla se leyó, pero no contiene filas con cantidades positivas reconocibles")
    return {
        "software": "Autodesk Revit" if software == "revit" else "Graphisoft Archicad",
        "delimitador": "tabulador" if delimitador == "\t" else delimitador,
        "encabezados": [str(celda).strip() for celda in filas[encabezado]],
        "total_filas": len(resultado),
        "filas": resultado,
        "aviso_precios": "Los precios del TXT se ignoran. Al agregar una fila se toma el precio vigente del catálogo SQL.",
    }
