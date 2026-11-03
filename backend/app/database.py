"""Conexión operativa local y acceso a bases documentales MongoDB."""

from flask import current_app
from pymongo import MongoClient
from pymongo.database import Database
from sqlalchemy import create_engine

from .config import DATA_DIR, OPERATIONAL_DATABASE_URL


DATA_DIR.mkdir(exist_ok=True)
if OPERATIONAL_DATABASE_URL.startswith("mysql"):
    raise RuntimeError("MySQL se reserva para el catálogo; configura SQLite para persistencia operativa.")
operational_engine = create_engine(
    OPERATIONAL_DATABASE_URL,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False} if OPERATIONAL_DATABASE_URL.startswith("sqlite") else {},
)


def init_mongo(app):
    """Inicializa un cliente Mongo compartido y registra las bases por dominio."""
    dns_servers = app.config.get("MONGO_DNS_SERVERS", ())
    if dns_servers:
        try:
            import dns.resolver
        except ImportError as error:
            raise RuntimeError("MONGO_DNS_SERVERS requiere el paquete dnspython.") from error
        resolver = dns.resolver.Resolver(configure=False)
        resolver.nameservers = list(dns_servers)
        dns.resolver.default_resolver = resolver

    client = MongoClient(
        app.config["MONGO_URI"],
        maxPoolSize=50,
        minPoolSize=5,
        serverSelectionTimeoutMS=3000,
        connectTimeoutMS=5000,
        socketTimeoutMS=10000,
        appname="BIMetrics-SaaS",
    )
    app.extensions["bimetrics_mongo_client"] = client
    app.extensions["bimetrics_users_db"] = client[app.config["MONGO_USERS_DB"]]
    app.extensions["bimetrics_activity_db"] = client[app.config["MONGO_ACTIVITY_DB"]]


def get_mongo_db(domain="activity") -> Database:
    """Devuelve la base Mongo configurada para ``users`` o ``activity``."""
    extension_key = "bimetrics_users_db" if domain == "users" else "bimetrics_activity_db"
    return current_app.extensions[extension_key]
