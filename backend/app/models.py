"""Esquema de la base de datos (según el diagrama ER)."""
from sqlalchemy import Column, Date, ForeignKey, Integer, MetaData, Numeric, String, Table, UniqueConstraint

meta = MetaData()

Table("USUARIOS", meta,
      Column("id_usuario", Integer, primary_key=True, autoincrement=True),
      Column("nombre_completo", String(150), nullable=False),
      Column("email", String(150), nullable=False, unique=True),
      Column("rol", String(50), nullable=False))
Table("CREDENCIALES", meta,
      Column("id_usuario", Integer, ForeignKey("USUARIOS.id_usuario", ondelete="CASCADE"), primary_key=True),
      Column("password_hash", String(255), nullable=False))
Table("AUTORIZACIONES_DATOS", meta,
      Column("id_autorizacion", Integer, primary_key=True, autoincrement=True),
      Column("id_usuario", Integer, ForeignKey("USUARIOS.id_usuario", ondelete="CASCADE"), nullable=False),
      Column("version_politica", String(30), nullable=False),
      Column("fecha_autorizacion", String(40), nullable=False))
Table("PROYECTOS", meta,
      Column("id_proyecto", Integer, primary_key=True, autoincrement=True),
      Column("id_usuario", Integer, ForeignKey("USUARIOS.id_usuario"), nullable=False),
      Column("nombre_obra", String(150), nullable=False),
      Column("cliente", String(150)),
      Column("ciudad", String(100)))
Table("PROYECTO_COLABORADORES", meta,
      Column("id_proyecto", Integer, ForeignKey("PROYECTOS.id_proyecto", ondelete="CASCADE"), primary_key=True),
      Column("id_usuario", Integer, ForeignKey("USUARIOS.id_usuario", ondelete="CASCADE"), primary_key=True),
      Column("invitado_por", Integer, ForeignKey("USUARIOS.id_usuario"), nullable=False))
Table("PRESUPUESTOS", meta,
      Column("id_presupuesto", Integer, primary_key=True, autoincrement=True),
      Column("id_proyecto", Integer, ForeignKey("PROYECTOS.id_proyecto"), nullable=False),
      Column("fecha_calculo", Date, nullable=False),
      Column("costo_total", Numeric(14, 2), default=0))
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
Table("DETALLE_PRESUPUESTO", meta,
      Column("id_detalle", Integer, primary_key=True, autoincrement=True),
      Column("id_presupuesto", Integer, ForeignKey("PRESUPUESTOS.id_presupuesto"), nullable=False),
      Column("id_insumo", Integer, ForeignKey("INSUMOS.id_insumo"), nullable=False),
      Column("cantidad", Numeric(14, 3), nullable=False),
      Column("costo_unitario_aplicado", Numeric(14, 2), nullable=False))

# Orden de creación (de padres a hijos); para borrar se usa el orden inverso
TABLAS = ("USUARIOS", "CREDENCIALES", "PROYECTOS", "PROYECTO_COLABORADORES", "INSUMOS", "PRECIOS_CIUDAD", "PRESUPUESTOS", "DETALLE_PRESUPUESTO")
