"""Conexión y gestión de persistencia políglota para BIMetrics.

Arquitectura Híbrida (SQL + NoSQL):
-----------------------------------
1. Base Relacional (SQLAlchemy Core - SQLite / MySQL):
   - Administra el núcleo transaccional ACID: usuarios, roles RBAC, presupuestos
     financieros y catálogo de insumos con trazabilidad histórica inmutable.

2. Base Documental NoSQL (PyMongo - MongoDB):
   - Colección: `actividades_bim`
   - ¿Por qué los logs de actividad BIM y los historiales de importación
     de archivos .txt de Revit / ArchiCAD se benefician de NoSQL sobre SQL?
     
     a) Polimorfismo y Esquema Dinámico (Schema Agility):
        Las tablas de cantidades exportadas en .txt desde Revit (parámetros compartidos)
        o ArchiCAD (propiedades IFC) varían drásticamente según la disciplina (Estructuras,
        Arquitectura, MEP) y versión del software. Un esquema relacional rígido obligaría
        a recurrir a antipatrones como EAV (Entity-Attribute-Value) o migraciones continuas
        con columnas nulas. Los documentos BSON permiten almacenar metadatos heterogéneos
        sin alterar la base de datos.
        
     b) Jerarquías y Grafo de Elementos Embebidos:
        BIM organiza elementos en jerarquías naturales (Proyecto -> Nivel -> Categoría ->
        Familia -> Parámetros). MongoDB permite embeber subdocumentos (`detalles_bim`)
        en un solo objeto, eliminando la necesidad de múltiples JOINs computacionalmente
        costosos al consultar historiales o advertencias de parsing.
        
     c) Alto Rendimiento de Ingesta y Operaciones Append-Only:
        El procesamiento de cómputos BIM genera ráfagas de logs, diferencias de cómputo,
        tokens no mapeados y telemetría. Al desacoplar estos eventos en MongoDB, se evita
        la contención de locks sobre las tablas financieras principales (PRESUPUESTOS y
        DETALLE_PRESUPUESTO).
        
     d) Aislamiento Transaccional (ACID vs BASE):
        Garantiza que una falla o cambio en la estructura de un archivo de software CAD/BIM
        no comprometa ni bloquee las transacciones contables críticas del presupuesto.
"""
from typing import Optional
from pymongo import MongoClient
from pymongo.database import Database
from sqlalchemy import create_engine

from .config import DATA_DIR, DB_URL, MONGO_DB_NAME, MONGO_URI

# ------------------------------------------------------------------------------
# 1. Base de Datos Relacional (SQLAlchemy Core)
# ------------------------------------------------------------------------------
DATA_DIR.mkdir(exist_ok=True)
engine = create_engine(DB_URL)

# ------------------------------------------------------------------------------
# 2. Base de Datos Documental NoSQL (PyMongo / MongoDB)
# ------------------------------------------------------------------------------
_mongo_client: Optional[MongoClient] = None


def get_mongo_client() -> MongoClient:
    """Obtiene o inicializa el cliente Singleton de PyMongo con pool de conexiones."""
    global _mongo_client
    if _mongo_client is None:
        _mongo_client = MongoClient(
            MONGO_URI,
            maxPoolSize=50,
            minPoolSize=5,
            serverSelectionTimeoutMS=3000,
            connectTimeoutMS=5000,
            socketTimeoutMS=10000,
            appname="BIMetrics-SaaS",
        )
    return _mongo_client


def get_mongo_db() -> Database:
    """Retorna la instancia de base de datos de MongoDB configurada."""
    client = get_mongo_client()
    return client[MONGO_DB_NAME]


def close_mongo_connection() -> None:
    """Cierra la conexión activa del cliente PyMongo si existe."""
    global _mongo_client
    if _mongo_client is not None:
        _mongo_client.close()
        _mongo_client = None

