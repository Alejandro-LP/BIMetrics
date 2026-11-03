"""Carga partidas y opciones de un CSV en el catálogo MySQL.

Uso desde backend/: ``python -m scripts.importar_catalogo_csv [ruta.csv]``.
Usa ``--dry-run`` para validar y contar los registros sin modificar la base.
"""

import argparse
import csv
import json
import os
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from urllib.parse import quote_plus

RAIZ_PROYECTO = Path(__file__).resolve().parents[2]
ARCHIVO_PREDETERMINADO = RAIZ_PROYECTO / "data" / "catalogo" / "catalogo_precios_colombia.csv"
ENCABEZADOS_REQUERIDOS = {
    "Codigo", "Unidad", "Descripcion", "Precio_Defecto", "Precios_Por_Opciones"
}
LOTE_VARIACIONES = 5000
LOTE_CODIGOS = 500


def _decimal(valor, contexto, permite_nulo=False):
    if valor is None or valor == "":
        if permite_nulo:
            return None
        raise ValueError(f"{contexto}: falta un valor numérico")
    try:
        numero = Decimal(str(valor))
    except (InvalidOperation, ValueError) as error:
        raise ValueError(f"{contexto}: valor numérico inválido {valor!r}") from error
    if not numero.is_finite():
        raise ValueError(f"{contexto}: el número debe ser finito")
    numero = numero.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if len(numero.as_tuple().digits) > 14:
        raise ValueError(f"{contexto}: el valor excede DECIMAL(14, 2)")
    return numero


def leer_catalogo(ruta):
    """Lee y valida las partidas y variaciones serializadas en la columna JSON."""
    partidas = []
    variaciones = []
    codigos = set()
    with Path(ruta).open("r", encoding="utf-8-sig", newline="") as archivo:
        lector = csv.DictReader(archivo)
        faltantes = ENCABEZADOS_REQUERIDOS - set(lector.fieldnames or ())
        if faltantes:
            raise ValueError(f"Faltan columnas CSV: {', '.join(sorted(faltantes))}")

        for numero_fila, fila in enumerate(lector, start=2):
            codigo = (fila.get("Codigo") or "").strip()
            unidad = (fila.get("Unidad") or "").strip()
            descripcion = (fila.get("Descripcion") or "").strip()
            if not codigo or not unidad or not descripcion:
                raise ValueError(f"Fila {numero_fila}: código, unidad y descripción son obligatorios")
            if codigo in codigos:
                raise ValueError(f"Fila {numero_fila}: código duplicado {codigo!r}")
            if len(codigo) > 50 or len(unidad) > 50:
                raise ValueError(f"Fila {numero_fila}: código o unidad exceden el tamaño de la tabla")
            codigos.add(codigo)
            partidas.append({
                "codigo": codigo,
                "unidad": unidad,
                "descripcion": descripcion,
                "precio_defecto": _decimal(fila.get("Precio_Defecto"), f"Fila {numero_fila}, precio_defecto"),
            })

            try:
                opciones = json.loads(fila.get("Precios_Por_Opciones") or "[]")
            except json.JSONDecodeError as error:
                raise ValueError(f"Fila {numero_fila}: JSON de opciones inválido: {error.msg}") from error
            if not isinstance(opciones, list):
                raise ValueError(f"Fila {numero_fila}: Precios_Por_Opciones debe ser una lista JSON")
            for indice, opcion in enumerate(opciones, start=1):
                contexto = f"Fila {numero_fila}, opción {indice}"
                if not isinstance(opcion, dict) or not isinstance(opcion.get("tipo"), str) or not opcion["tipo"].strip():
                    raise ValueError(f"{contexto}: se requiere un tipo de variación")
                valor_defecto = opcion.get("es_defecto", False)
                if valor_defecto is None:
                    valor_defecto = False
                if not isinstance(valor_defecto, bool):
                    raise ValueError(f"{contexto}: es_defecto debe ser booleano")
                nombre_opcion = opcion.get("opcion")
                parametro = opcion.get("parametro")
                valor_probado = opcion.get("valor_probado")
                if nombre_opcion is not None and not isinstance(nombre_opcion, str):
                    nombre_opcion = str(nombre_opcion)
                if parametro is not None and not isinstance(parametro, str):
                    parametro = str(parametro)
                if valor_probado is not None and not isinstance(valor_probado, str):
                    valor_probado = str(valor_probado)
                variaciones.append({
                    "codigo": codigo,
                    "tipo": opcion["tipo"].strip(),
                    "opcion": nombre_opcion,
                    "parametro": parametro,
                    "valor_probado": valor_probado,
                    "es_defecto": valor_defecto,
                    "precio": _decimal(opcion.get("precio"), f"{contexto}, precio", permite_nulo=True),
                })

    if not partidas:
        raise ValueError("El archivo no contiene partidas")
    return partidas, variaciones


def _ajustar_esquema_mysql(engine):
    """Actualiza columnas existentes para permitir los datos presentes en el CSV."""
    from sqlalchemy import Text, inspect, text

    inspector = inspect(engine)
    columnas = {columna["name"]: columna for columna in inspector.get_columns("variaciones_opciones")}
    opcion = columnas["opcion"]
    precio = columnas["precio"]
    sentencias = []
    if not opcion.get("nullable", True) or not isinstance(opcion["type"], Text):
        sentencias.append("ALTER TABLE variaciones_opciones MODIFY COLUMN opcion TEXT NULL")
    if not precio.get("nullable", True):
        sentencias.append("ALTER TABLE variaciones_opciones MODIFY COLUMN precio DECIMAL(14, 2) NULL")
    for sentencia in sentencias:
        with engine.begin() as connection:
            connection.execute(text(sentencia))


def importar(engine, partidas, variaciones):
    """Inserta el catálogo en MySQL sin inicializar los componentes Mongo de Flask."""
    from sqlalchemy import Boolean, Column, ForeignKey, Integer, MetaData, Numeric, String, Table, Text, delete
    from sqlalchemy.dialects.mysql import insert as mysql_insert

    if engine.dialect.name != "mysql":
        raise RuntimeError("El catálogo debe apuntar a MySQL para realizar la importación")

    metadata = MetaData()
    tabla_partidas = Table(
        "partidas", metadata,
        Column("codigo", String(50), primary_key=True),
        Column("unidad", String(50), nullable=False),
        Column("descripcion", Text, nullable=False),
        Column("precio_defecto", Numeric(14, 2), nullable=False, default=0),
        mysql_engine="InnoDB", mysql_charset="utf8mb4",
    )
    tabla_variaciones = Table(
        "variaciones_opciones", metadata,
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("codigo", String(50), ForeignKey("partidas.codigo", ondelete="CASCADE"), nullable=False, index=True),
        Column("tipo", String(100), nullable=False),
        Column("opcion", Text, nullable=True),
        Column("parametro", String(255)),
        Column("valor_probado", String(255)),
        Column("es_defecto", Boolean, nullable=False, default=False),
        Column("precio", Numeric(14, 2)),
        mysql_engine="InnoDB", mysql_charset="utf8mb4",
    )
    metadata.create_all(engine)
    _ajustar_esquema_mysql(engine)
    codigos = [partida["codigo"] for partida in partidas]
    with engine.begin() as connection:
        for inicio in range(0, len(partidas), LOTE_CODIGOS):
            lote = partidas[inicio:inicio + LOTE_CODIGOS]
            instruccion = mysql_insert(tabla_partidas).values(lote)
            instruccion = instruccion.on_duplicate_key_update(
                unidad=instruccion.inserted.unidad,
                descripcion=instruccion.inserted.descripcion,
                precio_defecto=instruccion.inserted.precio_defecto,
            )
            connection.execute(instruccion)
        for inicio in range(0, len(codigos), LOTE_CODIGOS):
            lote_codigos = codigos[inicio:inicio + LOTE_CODIGOS]
            connection.execute(delete(tabla_variaciones).where(tabla_variaciones.c.codigo.in_(lote_codigos)))
        for inicio in range(0, len(variaciones), LOTE_VARIACIONES):
            connection.execute(mysql_insert(tabla_variaciones).values(variaciones[inicio:inicio + LOTE_VARIACIONES]))


def main():
    """Ejecuta validación previa y, salvo modo seco, la carga del catálogo."""
    parser = argparse.ArgumentParser(description="Importa el catálogo BIMetrics desde CSV")
    parser.add_argument("archivo", nargs="?", type=Path, default=ARCHIVO_PREDETERMINADO)
    parser.add_argument("--dry-run", action="store_true", help="valida el archivo sin conectarse ni escribir")
    args = parser.parse_args()

    partidas, variaciones = leer_catalogo(args.archivo)
    print(f"Archivo: {args.archivo}")
    print(f"Partidas válidas: {len(partidas):,}")
    print(f"Variaciones válidas: {len(variaciones):,}")
    if args.dry_run:
        print("Validación correcta; no se modificó la base de datos.")
        return

    archivo_env = RAIZ_PROYECTO / ".env"
    if archivo_env.is_file():
        for linea in archivo_env.read_text(encoding="utf-8").splitlines():
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            clave, valor = linea.split("=", 1)
            valor = valor.strip().strip("\"'")
            os.environ.setdefault(clave.strip(), valor)
    catalog_url = os.getenv("CATALOG_DATABASE_URL") or os.getenv("DATABASE_URL") or os.getenv("DB_URL")
    if not catalog_url or not catalog_url.startswith("mysql"):
        user = quote_plus(os.getenv("MYSQL_USER", "root"))
        password = quote_plus(os.getenv("MYSQL_PASSWORD", ""))
        host = os.getenv("MYSQL_HOST", "localhost")
        port = os.getenv("MYSQL_PORT", "3306")
        database = os.getenv("MYSQL_DATABASE", "BIMetricsBD")
        catalog_url = f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}?charset=utf8mb4"
    elif catalog_url.startswith("mysql://"):
        catalog_url = catalog_url.replace("mysql://", "mysql+pymysql://", 1)
    if "charset=" not in catalog_url.lower():
        catalog_url += ("&" if "?" in catalog_url else "?") + "charset=utf8mb4"
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.exc import OperationalError
        engine = create_engine(catalog_url, pool_pre_ping=True)
    except ModuleNotFoundError as error:
        raise SystemExit(
            "Faltan dependencias SQL para importar el catálogo. Desde backend ejecuta: "
            "C:\\Python314\\python.exe -m pip install SQLAlchemy PyMySQL"
        ) from error
    try:
        importar(engine, partidas, variaciones)
    except Exception as error:
        if isinstance(error, OperationalError):
            raise SystemExit(
                "No se pudo conectar a MySQL. Revisa MYSQL_HOST, MYSQL_PORT, MYSQL_USER, "
                "MYSQL_PASSWORD y MYSQL_DATABASE en .env."
            ) from error
        raise
    finally:
        engine.dispose()
    print("Catálogo importado. Se actualizaron los códigos del archivo y sus variaciones.")


if __name__ == "__main__":
    main()
