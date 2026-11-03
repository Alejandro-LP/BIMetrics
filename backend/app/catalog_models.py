"""Modelo ORM del catálogo maestro almacenado en MySQL."""

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship

from .extensions import db


class Partida(db.Model):
    """Partida maestra del catálogo de construcción."""

    __tablename__ = "partidas"
    __table_args__ = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"}

    codigo = db.Column(String(50), primary_key=True)
    unidad = db.Column(String(50), nullable=False)
    descripcion = db.Column(Text, nullable=False)
    precio_defecto = db.Column(Numeric(14, 2), nullable=False, default=0)
    variaciones = relationship(
        "VariacionOpcion",
        back_populates="partida",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="VariacionOpcion.id",
    )


class VariacionOpcion(db.Model):
    """Opción paramétrica normalizada asociada a una partida."""

    __tablename__ = "variaciones_opciones"
    __table_args__ = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"}

    id = db.Column(Integer, primary_key=True, autoincrement=True)
    codigo = db.Column(
        String(50), ForeignKey("partidas.codigo", ondelete="CASCADE"), nullable=False, index=True
    )
    tipo = db.Column(String(100), nullable=False)
    opcion = db.Column(Text)
    parametro = db.Column(String(255))
    valor_probado = db.Column(String(255))
    es_defecto = db.Column(Boolean, nullable=False, default=False)
    precio = db.Column(Numeric(14, 2))

    partida = relationship("Partida", back_populates="variaciones")
