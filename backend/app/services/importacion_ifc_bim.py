"""Prepara una vista previa de cantidades explícitas de un archivo IFC."""

from collections import defaultdict
import math

import ifcopenshell
from ifcopenshell.util.element import get_type
from ifcopenshell.util.unit import get_prefix_multiplier, get_project_unit

from ..errors import ErrorApi
from .importacion_txt_bim import MAX_FILAS, sugerir_partidas

MAX_IFC_BYTES = 25 * 1024 * 1024

# El usuario elige una medida. Por elemento solo se usa una cantidad, aunque
# distintos conjuntos publiquen el mismo valor.
MEDIDAS = {
    "longitud": ("IfcQuantityLength", "LENGTHUNIT", "METRE", 1, "m", ("Length", "NetLength")),
    "area_neta": ("IfcQuantityArea", "AREAUNIT", "SQUARE_METRE", 2, "m²", ("NetSideArea", "NetArea", "NetFloorArea")),
    "area_bruta": ("IfcQuantityArea", "AREAUNIT", "SQUARE_METRE", 2, "m²", ("GrossSideArea", "GrossArea", "GrossFloorArea")),
    "volumen_neto": ("IfcQuantityVolume", "VOLUMEUNIT", "CUBIC_METRE", 3, "m³", ("NetVolume",)),
    "volumen_bruto": ("IfcQuantityVolume", "VOLUMEUNIT", "CUBIC_METRE", 3, "m³", ("GrossVolume",)),
}


def _factor_si(unidad, tipo, nombre_si, potencia):
    factor = 1.0
    # Las unidades de conversión contienen una unidad de referencia y un factor
    # (por ejemplo, pies cuadrados a metros cuadrados).
    for _ in range(8):
        if not unidad or getattr(unidad, "UnitType", None) != tipo:
            return None
        if unidad.is_a("IfcSIUnit") and unidad.Name == nombre_si:
            return factor * get_prefix_multiplier(unidad.Prefix) ** potencia
        if not unidad.is_a("IfcConversionBasedUnit") or unidad.is_a("IfcConversionBasedUnitWithOffset"):
            return None
        conversion = unidad.ConversionFactor
        factor *= float(conversion.ValueComponent.wrappedValue)
        unidad = conversion.UnitComponent
    return None


def _cantidad_elemento(elemento, medida, unidad_proyecto):
    clase, tipo, nombre_si, potencia, _, nombres = medida
    candidatos = []
    for relacion in elemento.IsDefinedBy:
        if not relacion.is_a("IfcRelDefinesByProperties"):
            continue
        conjunto = relacion.RelatingPropertyDefinition
        if not hasattr(conjunto, "is_a") or not conjunto.is_a("IfcElementQuantity"):
            continue
        nombre_conjunto = conjunto.Name or ""
        prioridad_conjunto = 0 if nombre_conjunto.startswith("Qto_") or nombre_conjunto == "BaseQuantities" else 1
        for cantidad in conjunto.Quantities:
            if cantidad.is_a(clase) and cantidad.Name in nombres:
                candidatos.append((prioridad_conjunto, nombres.index(cantidad.Name), cantidad.id(), cantidad))
    for _, _, _, cantidad in sorted(candidatos, key=lambda item: item[:3]):
        factor = _factor_si(cantidad.Unit or unidad_proyecto, tipo, nombre_si, potencia)
        if factor is not None:
            valor = float(cantidad[3]) * factor
            if math.isfinite(valor) and valor > 0:
                return cantidad.Name, valor
    return None


def leer_ifc_bim(contenido, metrica):
    """Extrae una medida por elemento y agrupa sin calcular geometría."""
    if metrica not in MEDIDAS:
        raise ErrorApi(400, "Selecciona la medida de obra que quieres extraer")
    if len(contenido) > MAX_IFC_BYTES:
        raise ErrorApi(413, "El archivo IFC supera el máximo de 25 MB")
    try:
        texto = contenido.decode("utf-8-sig")
    except UnicodeDecodeError:
        texto = contenido.decode("cp1252", errors="replace")
    if not texto.lstrip().startswith("ISO-10303-21;"):
        raise ErrorApi(400, "Sube un archivo .ifc de texto exportado desde Archicad")
    try:
        modelo = ifcopenshell.file.from_string(texto.lstrip())
        elementos = modelo.by_type("IfcElement")
    except (RuntimeError, ValueError) as error:
        raise ErrorApi(400, "No se pudo leer el IFC. Exporta de nuevo el modelo como IFC4 o IFC2x3.") from error

    medida = MEDIDAS[metrica]
    unidad_proyecto = get_project_unit(modelo, medida[1])
    grupos = defaultdict(lambda: [0.0, 0])
    omitidos = 0
    for elemento in elementos:
        if elemento.is_a("IfcFeatureElement") or elemento.is_a("IfcElementAssembly"):
            continue
        cantidad = _cantidad_elemento(elemento, medida, unidad_proyecto)
        if cantidad is None:
            omitidos += 1
            continue
        tipo = get_type(elemento)
        nombre = (getattr(tipo, "Name", None) or elemento.ObjectType or elemento.Name or elemento.is_a()).strip()
        campo, valor = cantidad
        grupo = grupos[nombre[:255], elemento.is_a(), campo]
        grupo[0] += valor
        grupo[1] += 1
        if len(grupos) > MAX_FILAS:
            raise ErrorApi(413, f"Hay más de {MAX_FILAS} grupos. Exporta solamente las plantas o elementos que necesites presupuestar.")

    if not grupos:
        raise ErrorApi(400, "El IFC no contiene esa medida con unidades válidas. Activa «Cantidades base IFC» en el traductor o elige otra medida.")

    filas = []
    for (nombre, clase, campo), (cantidad, elementos_grupo) in sorted(grupos.items()):
        filas.append({
            "indice": len(filas),
            "nombre": nombre,
            "cantidad": cantidad,
            "unidad": medida[4],
            "origen": f"{clase} · {campo} · {elementos_grupo} elemento(s)",
            "sugerencias": sugerir_partidas(nombre, unidad=medida[4]),
        })
    return {
        "software": f"IFC · {modelo.schema}",
        "total_filas": len(filas),
        "filas": filas,
        "elementos_omitidos": omitidos,
        "aviso_precios": "Revisa la medida y la partida sugerida. El precio se toma del catálogo SQL.",
    }
