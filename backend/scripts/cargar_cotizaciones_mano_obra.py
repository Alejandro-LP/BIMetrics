"""Carga tarifas referenciales 2026 de perfiles sugeridos en presupuestos.

Ejecutar desde ``backend``: ``python -m scripts.cargar_cotizaciones_mano_obra``.
Los valores son jornales indicativos, no ofertas vinculantes de contratistas.
"""

from datetime import date

from sqlalchemy import create_engine, text

from app.config import OPERATIONAL_DATABASE_URL
from app.models import meta

FECHA_REFERENCIA = date(2026, 11, 6)
CIUDADES = {
    "Bogotá": "principal",
    "Medellín": "principal",
    "Cali": "secundaria",
    "Barranquilla": "secundaria",
    "Cartagena": "mediana",
    "Bucaramanga": "mediana",
    "Pereira": "mediana",
    "Manizales": "mediana",
}

URL_MERCADO = "https://obramaestra.com/co/guias/cuanto-cobrar-mano-de-obra-construccion-colombia"
URL_APU_ELECTRICO = "https://www.solucionesexcel.com/apu/640-instalacion-de-acometida-domiciliaria/"
URL_APU_ESTRUCTURA = "https://www.solucionesexcel.com/apu/2194-estructura-metalica/"
URL_APU_CUBIERTA = "https://www.solucionesexcel.com/apu/2241-membrana-pvc-impermeabilizacion-1-5-mm/"
URL_CATEGORIAS_PRESTACIONALES = "https://oneestimate.ai/es/blog/tabla-precios-mano-obra-colombia-2026"
URL_MONTADOR = "https://agenciapublicadeempleo.sena.edu.co/spe-web/spe/demanda/solicitud-sintesis/4190648"
URL_COORDINADOR = "https://www.magneto365.com/co/empleos/coordinador-sst-con-curso-de-alturas-vigente-1117464"
URL_CONDUCTOR = "https://www.buk.co/recursos/estudios-de-gestion-de-personas/guia-salarial-colombia-2026"

# Valores diarios publicados por ciudad: mínimo/máximo COP, antes de confirmar
# prestaciones, recargos, AIU y condiciones particulares de la obra.
TARIFAS_MERCADO = {
    "ayudante": {"principal": (50_000, 65_000), "secundaria": (48_000, 62_000), "mediana": (42_000, 58_000)},
    "oficial": {"principal": (65_000, 85_000), "secundaria": (60_000, 78_000), "mediana": (55_000, 70_000)},
    "plomero": {"principal": (70_000, 90_000), "secundaria": (65_000, 82_000), "mediana": (55_000, 72_000)},
    "electricista": {"principal": (75_000, 95_000), "secundaria": (68_000, 88_000), "mediana": (58_000, 78_000)},
    "pintor": {"principal": (60_000, 78_000), "secundaria": (55_000, 72_000), "mediana": (48_000, 65_000)},
    "enchapador": {"principal": (100_000, 130_000), "secundaria": (90_000, 115_000), "mediana": (75_000, 100_000)},
    "carpintero": {"principal": (110_000, 140_000), "secundaria": (95_000, 125_000), "mediana": (80_000, 110_000)},
}

PERFILES = [
    {"nombre": "Montaje y desmontaje de andamios · Montador", "grupo": "montador", "unidad": "jornal", "fuente": "Agencia Pública de Empleo SENA", "url": URL_MONTADOR, "metodo": "Rango mensual publicado de $5.500.001–$6.000.000 convertido a jornal base dividiendo por 30; no confirma prestaciones ni recargos.", "prestaciones": None},
    {"nombre": "Ayudante de construcción", "grupo": "ayudante", "unidad": "jornal", "fuente": "Obra Maestra · mercado 2026", "url": URL_MERCADO, "metodo": "Punto medio del rango de peón/ayudante para la banda de ciudad publicada; la fuente no especifica prestaciones ni AIU.", "prestaciones": None},
    {"nombre": "Coordinador de trabajo en alturas", "grupo": "coordinador", "unidad": "jornal", "fuente": "Magneto · oferta publicada en 2026", "url": URL_COORDINADOR, "metodo": "Salario base anunciado de $2.500.000–$2.800.000 al mes, convertido a jornal dividiendo por 30. La oferta añade prestaciones y auxilio por separado; no incluye esos conceptos en el precio cargado.", "prestaciones": False},
    {"nombre": "Conductor de camión", "grupo": "conductor", "unidad": "jornal", "fuente": "Buk · guía salarial Colombia 2026", "url": URL_CONDUCTOR, "metodo": "Punto medio del rango mensual publicado ($2.615.000–$3.658.000) dividido por 30. Tarifa salarial base; confirmar jornada, viáticos, prestaciones y si transporte ya está incluido.", "prestaciones": False},
    {"nombre": "Oficial de construcción / armador de protección provisional", "grupo": "oficial", "unidad": "jornal", "fuente": "Obra Maestra · mercado 2026", "url": URL_MERCADO, "metodo": "Rango de oficial albañil usado como referencia de armado general. Confirmar material, altura, diseño y alcance antes de contratar.", "prestaciones": None},
    {"nombre": "Montador de estructuras metálicas", "grupo": "metalista_apu", "unidad": "jornal", "fuente": "Soluciones Excel · APU de estructura metálica 2026", "url": URL_APU_ESTRUCTURA, "metodo": "Tarifa de oficial de metalistería del APU, $215.944,95/jornal, con factor prestacional según la ficha; referencia publicada para Valle del Cauca, requiere ajuste local.", "prestaciones": True},
    {"nombre": "Operador de maquinaria", "grupo": "operador", "unidad": "jornal", "fuente": "OneEstimate · referencia laboral 2026", "url": URL_CATEGORIAS_PRESTACIONALES, "metodo": "Tarifa diaria cargada de referencia para operador de maquinaria pesada ($171.100); confirmar tipo de equipo, licencia, turno y ciudad.", "prestaciones": True},
    {"nombre": "Oficial de obra negra", "grupo": "oficial", "unidad": "jornal", "fuente": "Obra Maestra · mercado 2026", "url": URL_MERCADO, "metodo": "Rango de oficial albañil como perfil equivalente; la fuente no especifica prestaciones ni AIU.", "prestaciones": None},
    {"nombre": "Oficial mampostero", "grupo": "oficial", "unidad": "jornal", "fuente": "Obra Maestra · mercado 2026", "url": URL_MERCADO, "metodo": "Rango de oficial albañil como perfil equivalente para mampostería; ajustar por tipo de bloque, altura y rendimiento. La fuente no especifica prestaciones ni AIU.", "prestaciones": None},
    {"nombre": "Encofrador / formaletero", "grupo": "encofrador", "unidad": "jornal", "fuente": "OneEstimate · referencia laboral 2026", "url": URL_CATEGORIAS_PRESTACIONALES, "metodo": "Valor diario cargado de referencia para encofrador/carpintero de obra ($127.600); validar tipo de formaleta, rendimiento y jornada.", "prestaciones": True},
    {"nombre": "Armador de acero", "grupo": "armador_acero", "unidad": "jornal", "fuente": "OneEstimate · referencia laboral 2026", "url": URL_CATEGORIAS_PRESTACIONALES, "metodo": "Valor diario cargado de referencia para fierrero/armador ($130.700); validar diámetro, despiece y rendimiento.", "prestaciones": True},
    {"nombre": "Oficial electricista", "grupo": "electricista", "unidad": "jornal", "fuente": "Obra Maestra · mercado 2026", "url": URL_MERCADO, "metodo": "Rango de oficial electricista por ciudad; no incluye RETIE, materiales, horas extra ni AIU. APU público de instalación eléctrica consultado como contraste.", "prestaciones": None},
    {"nombre": "Auxiliar electricista", "grupo": "ayudante", "unidad": "jornal", "fuente": "Obra Maestra · mercado 2026", "url": URL_MERCADO, "metodo": "Rango de peón/ayudante como auxiliar. Confirmar competencia, riesgo eléctrico y prestaciones.", "prestaciones": None},
    {"nombre": "Oficial plomero / instalador hidrosanitario", "grupo": "plomero", "unidad": "jornal", "fuente": "Obra Maestra · mercado 2026", "url": URL_MERCADO, "metodo": "Rango publicado de oficial plomero por ciudad; no incluye materiales, pruebas, permisos ni AIU.", "prestaciones": None},
    {"nombre": "Auxiliar de plomería", "grupo": "ayudante", "unidad": "jornal", "fuente": "Obra Maestra · mercado 2026", "url": URL_MERCADO, "metodo": "Rango de peón/ayudante como auxiliar. Confirmar jornada y alcance de instalación.", "prestaciones": None},
    {"nombre": "Oficial de acabados", "grupo": "pintor", "unidad": "jornal", "fuente": "Obra Maestra · mercado 2026", "url": URL_MERCADO, "metodo": "Rango de pintor oficial como referencia general de acabados; el costo real depende de especialidad y superficie.", "prestaciones": None},
    {"nombre": "Pintor de obra", "grupo": "pintor", "unidad": "jornal", "fuente": "Obra Maestra · mercado 2026", "url": URL_MERCADO, "metodo": "Rango de pintor oficial por ciudad; no incluye materiales ni AIU.", "prestaciones": None},
    {"nombre": "Estucador", "grupo": "pintor", "unidad": "jornal", "fuente": "Obra Maestra · mercado 2026", "url": URL_MERCADO, "metodo": "Perfil aproximado por jornal de pintor oficial; la fuente publica precios por m² para estuco, así que convierte a jornada solo como referencia y debe reemplazarse por APU del alcance.", "prestaciones": None},
    {"nombre": "Enchapador / ceramista", "grupo": "enchapador", "unidad": "jornal", "fuente": "Obra Maestra · mercado 2026", "url": URL_MERCADO, "metodo": "Rango de enchapador/ceramista por ciudad; rendimiento depende del formato, patrón y estado del soporte.", "prestaciones": None},
    {"nombre": "Instalador de cubierta", "grupo": "carpintero", "unidad": "jornal", "fuente": "Obra Maestra · mercado 2026", "url": URL_MERCADO, "metodo": "Rango de carpintero de obra blanca como referencia para instalación liviana de cubierta; para impermeabilización, el APU público consultado usa oficial especializado a $215.944,95/jornal con factor prestacional.", "prestaciones": None},
    {"nombre": "Soldador / armador", "grupo": "soldador_apu", "unidad": "jornal", "fuente": "Soluciones Excel · APU de desmontaje de estructura metálica 2026", "url": "https://solucionesexcel.com/apu/732-desmontaje-y-traslado-de-estructuras-metalicas/", "metodo": "Tarifa de soldador de $215.944,95/jornal reportada en el análisis de mano de obra; incluye factor prestacional según la ficha, no alquiler de equipo.", "prestaciones": True},
]


def _rango(perfil, ciudad):
    grupo = perfil["grupo"]
    banda = CIUDADES[ciudad]
    if grupo in TARIFAS_MERCADO:
        return TARIFAS_MERCADO[grupo][banda]
    if grupo == "metalista_apu":
        return 215_944.95, 215_944.95
    if grupo == "soldador_apu":
        return 215_944.95, 215_944.95
    if grupo == "operador":
        return 171_100, 171_100
    if grupo == "encofrador":
        return 127_600, 127_600
    if grupo == "armador_acero":
        return 130_700, 130_700
    if grupo == "montador":
        return 5_500_001 / 30, 6_000_000 / 30
    if grupo == "coordinador":
        return 2_500_000 / 30, 2_800_000 / 30
    if grupo == "conductor":
        return 2_615_000 / 30, 3_658_000 / 30
    raise ValueError(f"No hay metodología de tarifa para {grupo}")


def main():
    engine = create_engine(OPERATIONAL_DATABASE_URL, pool_pre_ping=True)
    cotizaciones = meta.tables["COTIZACIONES_MANO_OBRA"]
    meta.create_all(engine, tables=[
        meta.tables["INSUMOS"],
        meta.tables["PRECIOS_CIUDAD"],
        cotizaciones,
    ])
    guardadas = 0
    try:
        with engine.begin() as connection:
            for perfil in PERFILES:
                id_insumo = connection.execute(
                    text("SELECT id_insumo FROM INSUMOS WHERE nombre_insumo=:nombre"),
                    {"nombre": perfil["nombre"]},
                ).scalar()
                if id_insumo is None:
                    id_insumo = connection.execute(
                        text("INSERT INTO INSUMOS (nombre_insumo, unidad_medida, costo_unitario) VALUES (:nombre, :unidad, 0)"),
                        {"nombre": perfil["nombre"], "unidad": perfil["unidad"]},
                    ).lastrowid
                for ciudad in CIUDADES:
                    minimo, maximo = _rango(perfil, ciudad)
                    minimo = round(minimo, 2)
                    maximo = round(maximo, 2)
                    referencial = round((minimo + maximo) / 2, 2)
                    precio_id = connection.execute(
                        text("SELECT id_precio FROM PRECIOS_CIUDAD WHERE id_insumo=:id AND ciudad=:ciudad"),
                        {"id": id_insumo, "ciudad": ciudad},
                    ).scalar()
                    if precio_id:
                        connection.execute(
                            text("UPDATE PRECIOS_CIUDAD SET costo_unitario=:precio WHERE id_precio=:id"),
                            {"precio": referencial, "id": precio_id},
                        )
                    else:
                        connection.execute(
                            text("INSERT INTO PRECIOS_CIUDAD (id_insumo, ciudad, costo_unitario) VALUES (:id, :ciudad, :precio)"),
                            {"id": id_insumo, "ciudad": ciudad, "precio": referencial},
                        )
                    cita_id = connection.execute(
                        text("SELECT id_cotizacion FROM COTIZACIONES_MANO_OBRA WHERE id_insumo=:id AND ciudad=:ciudad"),
                        {"id": id_insumo, "ciudad": ciudad},
                    ).scalar()
                    valores = {
                        "id": id_insumo, "ciudad": ciudad, "fecha": FECHA_REFERENCIA,
                        "minimo": minimo, "maximo": maximo, "referencial": referencial,
                        "fuente": perfil["fuente"], "url": perfil["url"],
                        "metodologia": perfil["metodo"], "prestaciones": perfil["prestaciones"],
                    }
                    if cita_id:
                        connection.execute(text(
                            "UPDATE COTIZACIONES_MANO_OBRA SET fecha_referencia=:fecha, valor_minimo=:minimo, "
                            "valor_maximo=:maximo, valor_referencial=:referencial, fuente=:fuente, fuente_url=:url, "
                            "metodologia=:metodologia, incluye_prestaciones=:prestaciones WHERE id_cotizacion=:cita"
                        ), {**valores, "cita": cita_id})
                    else:
                        connection.execute(text(
                            "INSERT INTO COTIZACIONES_MANO_OBRA (id_insumo, ciudad, fecha_referencia, valor_minimo, "
                            "valor_maximo, valor_referencial, fuente, fuente_url, metodologia, incluye_prestaciones) "
                            "VALUES (:id, :ciudad, :fecha, :minimo, :maximo, :referencial, :fuente, :url, :metodologia, :prestaciones)"
                        ), valores)
                    guardadas += 1
    finally:
        engine.dispose()
    print(f"Cotizaciones referenciales cargadas: {guardadas} para {len(PERFILES)} perfiles y {len(CIUDADES)} ciudades.")
    print("Son valores de referencia 2026; revise prestaciones, jornada, alcance y AIU antes de contratar.")


if __name__ == "__main__":
    main()
