"""Consultas de catálogo de partidas y sus opciones de variación."""
from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload

from ..catalog_models import Partida
from ..extensions import db


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
    return [serializar_partida(partida, incluir_mano_obra=True) for partida in partidas]


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
