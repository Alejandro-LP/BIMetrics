"""Crea y carga recomendaciones documentadas de mano de obra en MySQL.

Ejecutar desde ``backend`` con el entorno virtual activo:
``python -m scripts.cargar_recomendaciones_mano_obra``

El proceso es idempotente y no fija salarios, cantidades ni rendimientos: deben
definirse según alcance, cotización, ciudad y condiciones de cada obra.
"""

from sqlalchemy import create_engine, select
from sqlalchemy.dialects.mysql import insert as mysql_insert

from app.catalog_models import Partida, RecomendacionManoObra
from app.config import CATALOG_DATABASE_URL

CUOC_ANDAMIOS = "https://ocupacol.mintrabajo.gov.co/Profile/OccupationalProfile/71190"
CUOC_AYUDANTES = "https://ocupacol.mintrabajo.gov.co/Profile/OccupationalProfile/93130"
CUOC_CONDUCTORES = "https://ocupacol.mintrabajo.gov.co/Profile/OccupationalProfile/83320"
CUOC_ESTRUCTURAS = "https://ocupacol.mintrabajo.gov.co/Profile/OccupationalProfile/72140"
RESOLUCION_ALTURAS = "https://www.cancilleria.gov.co/normograma/compilacion/docs/resolucion_mtra_4272_2021.htm"
APU_VIVIENDA = "https://www.minvivienda.gov.co/sites/default/files/normativa/anexo-7-anexo-tecnico-vr_0.pdf"

RECOMENDACIONES = [
    {
        "codigo": "0XA110",
        "perfil": "Montador de andamios",
        "tipo": "condicional",
        "fundamento": "Incluir solo si el alquiler no incorpora montaje y desmontaje; comprobar el alcance del proveedor para evitar duplicar el ítem 0XA130.",
        "fuente_url": CUOC_ANDAMIOS,
        "prioridad": 1,
    },
    {
        "codigo": "0XA110",
        "perfil": "Ayudante de construcción",
        "tipo": "condicional",
        "fundamento": "Apoyo de cargue, descargue y acopio únicamente si esas labores no están incluidas en el suministro o transporte contratado.",
        "fuente_url": CUOC_AYUDANTES,
        "prioridad": 2,
    },
    {
        "codigo": "0XA120",
        "perfil": "Conductor de camión",
        "tipo": "condicional",
        "fundamento": "Aplicable cuando el transporte se contrata o presupuesta por separado; no volver a cargarlo si ya está incluido en la tarifa de transporte.",
        "fuente_url": CUOC_CONDUCTORES,
        "prioridad": 1,
    },
    {
        "codigo": "0XA120",
        "perfil": "Ayudante de construcción",
        "tipo": "condicional",
        "fundamento": "Apoyo para cargar, descargar y organizar componentes cuando el servicio de transporte no incluya estas labores.",
        "fuente_url": CUOC_AYUDANTES,
        "prioridad": 2,
    },
    {
        "codigo": "0XA130",
        "perfil": "Montador de andamios",
        "tipo": "sugerido",
        "fundamento": "Perfil principal para armar y desmontar el sistema. Quien realice esta función requiere capacitación específica conforme a las condiciones aplicables de trabajo en alturas.",
        "fuente_url": RESOLUCION_ALTURAS,
        "prioridad": 1,
    },
    {
        "codigo": "0XA130",
        "perfil": "Ayudante técnico de andamios / ayudante de construcción",
        "tipo": "sugerido",
        "fundamento": "Apoya el movimiento, entrega y aseguramiento de componentes durante el montaje y desmontaje; las funciones en altura deben asignarse según capacitación y procedimiento seguro.",
        "fuente_url": CUOC_AYUDANTES,
        "prioridad": 2,
    },
    {
        "codigo": "0XA130",
        "perfil": "Coordinador de trabajo en alturas",
        "tipo": "condicional",
        "fundamento": "Incluir según el riesgo, el programa de prevención y los roles exigidos para el trabajo concreto; no se presume una dedicación exclusiva por cada unidad de andamio.",
        "fuente_url": RESOLUCION_ALTURAS,
        "prioridad": 3,
    },
    {
        "codigo": "0XA140",
        "perfil": "Montador de andamios",
        "tipo": "sugerido",
        "fundamento": "Instala y fija la protección sobre el andamio. Si la labor implica trabajo en alturas, el empleador debe verificar capacitación, sistema de acceso y controles de riesgo aplicables.",
        "fuente_url": RESOLUCION_ALTURAS,
        "prioridad": 1,
    },
    {
        "codigo": "0XA140",
        "perfil": "Ayudante de construcción",
        "tipo": "sugerido",
        "fundamento": "Apoya alistamiento, izado, sujeción y acopio de la lona; asignar tareas en altura solo si cuenta con la formación requerida.",
        "fuente_url": CUOC_AYUDANTES,
        "prioridad": 2,
    },
    {
        "codigo": "YCM040",
        "perfil": "Oficial de construcción / armador de protección provisional",
        "tipo": "sugerido",
        "fundamento": "La instalación de protección peatonal requiere personal que replantee, arme y verifique el sistema de acuerdo con el diseño y las especificaciones del proyecto.",
        "fuente_url": APU_VIVIENDA,
        "prioridad": 1,
    },
    {
        "codigo": "YCM040",
        "perfil": "Ayudante de construcción",
        "tipo": "sugerido",
        "fundamento": "Apoya cargue, descargue, acopio, señalización y montaje. Los APU públicos consultados usan cuadrillas de oficial y ayudante para actividades constructivas comparables.",
        "fuente_url": CUOC_AYUDANTES,
        "prioridad": 2,
    },
    {
        "codigo": "YCM040",
        "perfil": "Montador de estructuras metálicas",
        "tipo": "condicional",
        "fundamento": "Aplicar solo si los planos o ficha del sistema especifican estructura metálica; no se presupone el material de esta partida.",
        "fuente_url": CUOC_ESTRUCTURAS,
        "prioridad": 3,
    },
    {
        "codigo": "YCM045",
        "perfil": "Oficial de construcción / armador de protección provisional",
        "tipo": "sugerido",
        "fundamento": "La instalación de protección peatonal requiere personal que replantee, arme y verifique el sistema de acuerdo con el diseño y las especificaciones del proyecto.",
        "fuente_url": APU_VIVIENDA,
        "prioridad": 1,
    },
    {
        "codigo": "YCM045",
        "perfil": "Ayudante de construcción",
        "tipo": "sugerido",
        "fundamento": "Apoya cargue, descargue, acopio, señalización y montaje. Los APU públicos consultados usan cuadrillas de oficial y ayudante para actividades constructivas comparables.",
        "fuente_url": CUOC_AYUDANTES,
        "prioridad": 2,
    },
    {
        "codigo": "YCM045",
        "perfil": "Montador de estructuras metálicas",
        "tipo": "condicional",
        "fundamento": "Aplicar solo si los planos o ficha del sistema especifican estructura metálica; no se presupone el material de esta partida.",
        "fuente_url": CUOC_ESTRUCTURAS,
        "prioridad": 3,
    },
]


def main():
    """Crea la tabla si falta y actualiza las recomendaciones del catálogo SQL."""
    engine = create_engine(CATALOG_DATABASE_URL, pool_pre_ping=True)
    if engine.dialect.name != "mysql":
        raise SystemExit("El catálogo de mano de obra debe guardarse en MySQL.")

    tabla = RecomendacionManoObra.__table__
    tabla.create(engine, checkfirst=True)
    codigos = sorted({item["codigo"] for item in RECOMENDACIONES})
    try:
        with engine.begin() as connection:
            existentes = set(connection.execute(
                select(Partida.codigo).where(Partida.codigo.in_(codigos))
            ).scalars())
            faltantes = sorted(set(codigos) - existentes)
            if faltantes:
                raise RuntimeError(f"No existen estas partidas en el catálogo: {', '.join(faltantes)}")

            instruccion = mysql_insert(tabla).values(RECOMENDACIONES)
            instruccion = instruccion.on_duplicate_key_update(
                tipo=instruccion.inserted.tipo,
                fundamento=instruccion.inserted.fundamento,
                fuente_url=instruccion.inserted.fuente_url,
                prioridad=instruccion.inserted.prioridad,
            )
            connection.execute(instruccion)
            total = connection.execute(
                select(RecomendacionManoObra.codigo)
                .where(RecomendacionManoObra.codigo.in_(codigos))
            ).scalars().all()
    finally:
        engine.dispose()

    print(f"Recomendaciones SQL guardadas: {len(total)} en {len(codigos)} partidas.")


if __name__ == "__main__":
    main()
