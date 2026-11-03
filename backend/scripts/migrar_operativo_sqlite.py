"""Migra tablas operativas SQL heredadas a la base SQLite separada.

Configura ``LEGACY_OPERATIONAL_DATABASE_URL`` y ``OPERATIONAL_DATABASE_URL``.
Ejecuta desde ``backend/``: ``python -m scripts.migrar_operativo_sqlite``.
La migración conserva IDs y no modifica ni borra la base de origen.
"""

import os

from sqlalchemy import MetaData, Table, create_engine, inspect, select, text

from app.config import OPERATIONAL_DATABASE_URL
from app.database import operational_engine
from app.models import TABLAS, meta


def main():
    """Copia filas en orden de dependencias si el destino está vacío."""
    legacy_url = os.getenv("LEGACY_OPERATIONAL_DATABASE_URL")
    if not legacy_url:
        raise RuntimeError("Define LEGACY_OPERATIONAL_DATABASE_URL para identificar la base SQL de origen.")
    if not OPERATIONAL_DATABASE_URL.startswith("sqlite"):
        raise RuntimeError("El destino operativo debe ser SQLite; MySQL queda reservado al catálogo.")

    source_engine = create_engine(legacy_url, pool_pre_ping=True)
    meta.create_all(operational_engine)
    source_inspector = inspect(source_engine)
    missing = [tabla for tabla in TABLAS if not source_inspector.has_table(tabla)]
    if missing:
        raise RuntimeError(f"Faltan tablas operativas en el origen: {', '.join(missing)}")

    with operational_engine.connect() as target:
        counts = {
            tabla: target.execute(text(f"SELECT COUNT(*) FROM {tabla}")).scalar()
            for tabla in TABLAS
        }
    if any(counts.values()):
        raise RuntimeError("El destino operativo no está vacío; no se modificó ningún dato.")

    source_metadata = MetaData()
    report = {}
    with source_engine.connect() as source, operational_engine.begin() as target:
        for nombre in TABLAS:
            tabla_origen = Table(nombre, source_metadata, autoload_with=source_engine)
            filas = source.execute(select(tabla_origen)).mappings().all()
            if filas:
                tabla_destino = meta.tables[nombre]
                columnas_destino = {columna.name for columna in tabla_destino.columns}
                lote = [
                    {clave: valor for clave, valor in fila.items() if clave in columnas_destino}
                    for fila in filas
                ]
                target.execute(tabla_destino.insert(), lote)
            report[nombre] = len(filas)

    source_engine.dispose()
    print("Registros migrados:", ", ".join(f"{tabla}: {cantidad}" for tabla, cantidad in report.items()))


if __name__ == "__main__":
    main()
