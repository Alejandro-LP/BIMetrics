"""Consultas de catálogo de partidas y sus opciones de variación."""
import re
import unicodedata

from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload

from ..catalog_models import Partida
from ..extensions import db


def _normalizar_busqueda(valor):
    """Normaliza tildes y signos para comparar palabras del catálogo."""
    texto = unicodedata.normalize("NFKD", str(valor or "").casefold())
    texto = "".join(caracter for caracter in texto if not unicodedata.combining(caracter))
    return re.findall(r"[a-z0-9]+", texto)


def _distancia_edicion_adyacente(izquierda, derecha, limite):
    """Distancia de edición con transposición adyacente y corte por umbral."""
    if abs(len(izquierda) - len(derecha)) > limite:
        return limite + 1
    anterior_anterior = None
    anterior = list(range(len(derecha) + 1))
    for indice_i, caracter_i in enumerate(izquierda, start=1):
        actual = [indice_i] + [0] * len(derecha)
        for indice_j, caracter_j in enumerate(derecha, start=1):
            actual[indice_j] = min(
                actual[indice_j - 1] + 1,
                anterior[indice_j] + 1,
                anterior[indice_j - 1] + (caracter_i != caracter_j),
            )
            if (
                anterior_anterior is not None
                and indice_i > 1
                and indice_j > 1
                and caracter_i == derecha[indice_j - 2]
                and izquierda[indice_i - 2] == caracter_j
            ):
                actual[indice_j] = min(actual[indice_j], anterior_anterior[indice_j - 2] + 1)
        if min(actual) > limite:
            return limite + 1
        anterior_anterior, anterior = anterior, actual
    return anterior[-1]


def _buscar_aproximadas(texto, limit, offset):
    """Busca errores tipográficos menores sobre candidatos leídos desde SQL."""
    terminos = list(dict.fromkeys(_normalizar_busqueda(texto)))
    if not terminos:
        return []

    filas_catalogo = db.session.execute(
        select(Partida.codigo, Partida.unidad, Partida.descripcion, Partida.precio_defecto)
    ).all()
    clasificadas = []
    for codigo, unidad, descripcion, precio in filas_catalogo:
        palabras = set(_normalizar_busqueda(f"{codigo} {descripcion}"))
        distancias = []
        for termino in terminos:
            if termino in palabras:
                distancias.append(0)
                continue
            if len(termino) <= 3:
                break
            max_ediciones = 1 if len(termino) < 8 else 2
            distancia = min(
                (_distancia_edicion_adyacente(termino, palabra, max_ediciones) for palabra in palabras),
                default=max_ediciones + 1,
            )
            if distancia > max_ediciones:
                break
            distancias.append(distancia)
        if len(distancias) == len(terminos):
            similitud = sum(
                1 - distancia / max(1, len(termino))
                for termino, distancia in zip(terminos, distancias)
            ) / len(terminos)
            clasificadas.append((similitud, codigo))

    clasificadas.sort(key=lambda item: (-item[0], item[1]))
    codigos = [codigo for _, codigo in clasificadas[offset:offset + limit]]
    if not codigos:
        return []
    partidas = db.session.scalars(
        select(Partida)
        .where(Partida.codigo.in_(codigos))
        .options(selectinload(Partida.recomendaciones_mano_obra))
    ).all()
    por_codigo = {partida.codigo: partida for partida in partidas}
    resultados = []
    for codigo in codigos:
        partida = por_codigo.get(codigo)
        if partida:
            resultado = serializar_partida(partida, incluir_mano_obra=True)
            resultado["coincidencia_aproximada"] = True
            resultados.append(resultado)
    return resultados


def _serializar_variacion(variacion):
    return {
        "id": variacion.id,
        "codigo": variacion.codigo,
        "tipo": variacion.tipo,
        "opcion": variacion.opcion,
        "parametro": variacion.parametro,
        "valor_probado": variacion.valor_probado,
        "es_defecto": variacion.es_defecto,
        "precio": float(variacion.precio) if variacion.precio is not None else None,
    }


def serializar_partida(partida, incluir_variaciones=False, incluir_mano_obra=False):
    resultado = {
        "codigo": partida.codigo,
        "unidad": partida.unidad,
        "descripcion": partida.descripcion,
        "precio_defecto": float(partida.precio_defecto) if partida.precio_defecto is not None else None,
    }
    if incluir_variaciones:
        resultado["variaciones"] = [_serializar_variacion(item) for item in partida.variaciones]
    if incluir_mano_obra:
        resultado["recomendaciones_mano_obra"] = [
            {
                "perfil": item.perfil,
                "tipo": item.tipo,
                "fundamento": item.fundamento,
                "fuente_url": item.fuente_url,
                "rendimiento_por_jornal": (
                    float(item.rendimiento_por_jornal)
                    if item.rendimiento_por_jornal is not None else None
                ),
            }
            for item in partida.recomendaciones_mano_obra
        ]
    return resultado


def listar_partidas(limit=50, offset=0):
    partidas = db.session.scalars(
        select(Partida).order_by(Partida.codigo).limit(limit).offset(offset)
    ).all()
    return [serializar_partida(partida) for partida in partidas]


def buscar_partidas(texto, limit=50, offset=0):
    partidas = db.session.scalars(
        select(Partida)
        .where(or_(Partida.codigo.ilike(f"%{texto}%"), Partida.descripcion.ilike(f"%{texto}%")))
        .options(selectinload(Partida.recomendaciones_mano_obra))
        .order_by(Partida.codigo)
        .limit(limit)
        .offset(offset)
    ).all()
    if partidas:
        return [serializar_partida(partida, incluir_mano_obra=True) for partida in partidas]
    return _buscar_aproximadas(texto, limit, offset)


def obtener_partida(codigo):
    partida = db.session.scalar(
        select(Partida)
        .where(Partida.codigo == codigo)
        .options(
            selectinload(Partida.variaciones),
            selectinload(Partida.recomendaciones_mano_obra),
        )
    )
    return serializar_partida(partida, incluir_variaciones=True, incluir_mano_obra=True) if partida else None
