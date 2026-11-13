"""Esquema de la base de datos (según el diagrama ER)."""
from sqlalchemy import (
    Boolean,
    DateTime,
    Column,
    Date,
    ForeignKey,
    Integer,
    MetaData,
    Numeric,
    String,
    Table,
    Text,
    UniqueConstraint,
)

meta = MetaData()

Table("PROYECTOS", meta,
      Column("id_proyecto", Integer, primary_key=True, autoincrement=True),
      Column("id_usuario", Integer, nullable=False),
      Column("nombre_obra", String(150), nullable=False),
      Column("cliente", String(150)),
      Column("ciudad", String(100)))
Table("PROYECTO_COLABORADORES", meta,
      Column("id_proyecto", Integer, ForeignKey("PROYECTOS.id_proyecto", ondelete="CASCADE"), primary_key=True),
      Column("id_usuario", Integer, primary_key=True),
      Column("invitado_por", Integer, nullable=False))
Table("PROYECTO_INVITACIONES", meta,
      Column("id_invitacion", Integer, primary_key=True, autoincrement=True),
      Column("id_proyecto", Integer, ForeignKey("PROYECTOS.id_proyecto", ondelete="CASCADE"), nullable=False, index=True),
      Column("codigo_hash", String(64), nullable=False, unique=True),
      Column("rol", String(20), nullable=False),
      Column("creado_por", Integer, nullable=False),
      Column("creado_en", DateTime, nullable=False),
      Column("expira_en", DateTime, nullable=False),
      Column("aceptado_por", Integer),
      Column("aceptado_en", DateTime))
Table("PRESUPUESTOS", meta,
      Column("id_presupuesto", Integer, primary_key=True, autoincrement=True),
      Column("id_proyecto", Integer, ForeignKey("PROYECTOS.id_proyecto"), nullable=False),
      Column("fecha_calculo", Date, nullable=False),
      Column("costo_total", Numeric(14, 2), default=0),
      Column("porcentaje_administracion", Numeric(5, 2), nullable=False, default=0),
      Column("porcentaje_imprevistos", Numeric(5, 2), nullable=False, default=0),
      Column("porcentaje_utilidad", Numeric(5, 2), nullable=False, default=0))
Table("INSUMOS", meta,
      Column("id_insumo", Integer, primary_key=True, autoincrement=True),
      Column("nombre_insumo", String(150), nullable=False, unique=True),
      Column("unidad_medida", String(30), nullable=False),
      Column("costo_unitario", Numeric(14, 2), nullable=False))
Table("PRECIOS_CIUDAD", meta,
      Column("id_precio", Integer, primary_key=True, autoincrement=True),
      Column("id_insumo", Integer, ForeignKey("INSUMOS.id_insumo", ondelete="CASCADE"), nullable=False),
      Column("ciudad", String(100), nullable=False),
      Column("costo_unitario", Numeric(14, 2), nullable=False),
      UniqueConstraint("id_insumo", "ciudad", name="uq_precio_insumo_ciudad"))
Table("COTIZACIONES_MANO_OBRA", meta,
      Column("id_cotizacion", Integer, primary_key=True, autoincrement=True),
      Column("id_insumo", Integer, ForeignKey("INSUMOS.id_insumo", ondelete="CASCADE"), nullable=False),
      Column("ciudad", String(100), nullable=False),
      Column("fecha_referencia", Date, nullable=False),
      Column("valor_minimo", Numeric(14, 2), nullable=False),
      Column("valor_maximo", Numeric(14, 2), nullable=False),
      Column("valor_referencial", Numeric(14, 2), nullable=False),
      Column("fuente", String(150), nullable=False),
      Column("fuente_url", Text, nullable=False),
      Column("metodologia", Text, nullable=False),
      Column("incluye_prestaciones", Boolean),
      UniqueConstraint("id_insumo", "ciudad", name="uq_cotizacion_mano_obra_ciudad"))
Table("DETALLE_PRESUPUESTO", meta,
      Column("id_detalle", Integer, primary_key=True, autoincrement=True),
      Column("id_presupuesto", Integer, ForeignKey("PRESUPUESTOS.id_presupuesto"), nullable=False),
      Column("id_insumo", Integer, ForeignKey("INSUMOS.id_insumo"), nullable=False),
      Column("cantidad", Numeric(14, 3), nullable=False),
      Column("costo_unitario_aplicado", Numeric(14, 2), nullable=False),
      Column("capitulo", String(100)))

# Orden de creación (de padres a hijos); para borrar se usa el orden inverso
TABLAS = (
    "PROYECTOS",
    "PROYECTO_COLABORADORES",
    "PROYECTO_INVITACIONES",
    "INSUMOS",
    "PRECIOS_CIUDAD",
    "COTIZACIONES_MANO_OBRA",
    "PRESUPUESTOS",
    "DETALLE_PRESUPUESTO",
)
