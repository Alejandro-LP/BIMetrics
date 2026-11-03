"""Genera un volcado SQL importable del catálogo colombiano de precios.

Uso desde backend/: ``python -m scripts.generar_catalogo_sql``.
"""

import argparse
import csv
import json
from pathlib import Path

RAIZ_PROYECTO = Path(__file__).resolve().parents[2]
CSV_PREDETERMINADO = RAIZ_PROYECTO / "data" / "catalogo" / "catalogo_precios_colombia.csv"
SQL_PREDETERMINADO = RAIZ_PROYECTO / "data" / "catalogo" / "catalogo_precios_colombia.sql"
TAMANO_LOTE = 250


def literal_sql(valor):
    """Convierte un valor de texto en literal compatible con MySQL utf8mb4."""
    if valor is None or valor == "":
        return "NULL"
    texto = str(valor).replace("\\", "\\\\").replace("'", "''")
    texto = texto.replace("\r", "\\r").replace("\n", "\\n").replace("\0", "\\0")
    return f"'{texto}'"


def generar(archivo_csv, archivo_sql):
    """Escribe esquema y datos sin conectarse ni modificar ninguna base."""
    partidas = []
    variaciones = []
    with Path(archivo_csv).open("r", encoding="utf-8-sig", newline="") as archivo:
        lector = csv.DictReader(archivo)
        for numero_fila, fila in enumerate(lector, start=2):
            codigo = (fila.get("Codigo") or "").strip()
            unidad = (fila.get("Unidad") or "").strip()
            descripcion = (fila.get("Descripcion") or "").strip()
            if not codigo or not unidad or not descripcion:
                raise ValueError(f"Fila {numero_fila}: faltan código, unidad o descripción")
            partidas.append((codigo, unidad, descripcion, fila["Precio_Defecto"]))
            opciones = json.loads(fila.get("Precios_Por_Opciones") or "[]")
            if not isinstance(opciones, list):
                raise ValueError(f"Fila {numero_fila}: las opciones deben ser una lista JSON")
            for opcion in opciones:
                variaciones.append((
                    codigo,
                    opcion["tipo"],
                    opcion.get("opcion"),
                    opcion.get("parametro"),
                    opcion.get("valor_probado"),
                    1 if opcion.get("es_defecto", False) else 0,
                    opcion.get("precio"),
                ))

    ruta = Path(archivo_sql)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("w", encoding="utf-8", newline="\n") as salida:
        salida.write("-- Catálogo colombiano de precios de BIMetrics.\n")
        salida.write("-- Fuente: data/catalogo/catalogo_precios_colombia.csv\n")
        salida.write("-- Motor destino: MySQL/MariaDB. Seleccione la base de datos antes de importar.\n")
        salida.write("SET NAMES utf8mb4;\n\n")
        salida.write("CREATE TABLE IF NOT EXISTS partidas (\n")
        salida.write("  codigo VARCHAR(50) NOT NULL PRIMARY KEY,\n")
        salida.write("  unidad VARCHAR(50) NOT NULL,\n")
        salida.write("  descripcion TEXT NOT NULL,\n")
        salida.write("  precio_defecto DECIMAL(14,2) NOT NULL DEFAULT 0\n")
        salida.write(") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;\n\n")
        salida.write("CREATE TABLE IF NOT EXISTS variaciones_opciones (\n")
        salida.write("  id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,\n")
        salida.write("  codigo VARCHAR(50) NOT NULL,\n")
        salida.write("  tipo VARCHAR(100) NOT NULL,\n")
        salida.write("  opcion TEXT NULL,\n")
        salida.write("  parametro VARCHAR(255) NULL,\n")
        salida.write("  valor_probado VARCHAR(255) NULL,\n")
        salida.write("  es_defecto TINYINT(1) NOT NULL DEFAULT 0,\n")
        salida.write("  precio DECIMAL(14,2) NULL,\n")
        salida.write("  INDEX ix_variaciones_opciones_codigo (codigo),\n")
        salida.write("  CONSTRAINT fk_variaciones_opciones_partida FOREIGN KEY (codigo) "
                     "REFERENCES partidas (codigo) ON DELETE CASCADE\n")
        salida.write(") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;\n\n")
        salida.write("START TRANSACTION;\n")
        for inicio in range(0, len(partidas), TAMANO_LOTE):
            lote = partidas[inicio:inicio + TAMANO_LOTE]
            filas = ["(" + ", ".join((literal_sql(codigo), literal_sql(unidad), literal_sql(descripcion), precio)) + ")"
                     for codigo, unidad, descripcion, precio in lote]
            salida.write("INSERT INTO partidas (codigo, unidad, descripcion, precio_defecto) VALUES\n")
            salida.write(",\n".join(filas))
            salida.write("\nON DUPLICATE KEY UPDATE unidad=VALUES(unidad), "
                         "descripcion=VALUES(descripcion), precio_defecto=VALUES(precio_defecto);\n\n")

        codigos = [partida[0] for partida in partidas]
        for inicio in range(0, len(codigos), TAMANO_LOTE):
            lote = ", ".join(literal_sql(codigo) for codigo in codigos[inicio:inicio + TAMANO_LOTE])
            salida.write(f"DELETE FROM variaciones_opciones WHERE codigo IN ({lote});\n")
        salida.write("\n")
        for inicio in range(0, len(variaciones), TAMANO_LOTE):
            filas = []
            for codigo, tipo, opcion, parametro, valor, defecto, precio in variaciones[inicio:inicio + TAMANO_LOTE]:
                filas.append("(" + ", ".join((
                    literal_sql(codigo), literal_sql(tipo), literal_sql(opcion),
                    literal_sql(parametro), literal_sql(valor), str(defecto),
                    "NULL" if precio is None or precio == "" else str(precio),
                )) + ")")
            salida.write("INSERT INTO variaciones_opciones "
                         "(codigo, tipo, opcion, parametro, valor_probado, es_defecto, precio) VALUES\n")
            salida.write(",\n".join(filas) + ";\n\n")
        salida.write("COMMIT;\n")
    return len(partidas), len(variaciones), ruta


def main():
    parser = argparse.ArgumentParser(description="Genera el SQL del catálogo de precios desde el CSV")
    parser.add_argument("--csv", type=Path, default=CSV_PREDETERMINADO)
    parser.add_argument("--output", type=Path, default=SQL_PREDETERMINADO)
    args = parser.parse_args()
    partidas, variaciones, salida = generar(args.csv, args.output)
    print(f"Partidas: {partidas:,}")
    print(f"Variaciones: {variaciones:,}")
    print(f"Archivo SQL: {salida}")


if __name__ == "__main__":
    main()
