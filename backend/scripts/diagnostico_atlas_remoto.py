"""Diagnostica una conexión directa a Atlas desde otro equipo sin guardar credenciales."""

from getpass import getpass

from pymongo import MongoClient
from pymongo.errors import PyMongoError


DEFAULT_HOST = "bimetrics.367yjhx.mongodb.net"


def main() -> int:
    host = input(f"Host Atlas [{DEFAULT_HOST}]: ").strip() or DEFAULT_HOST
    username = input("Usuario de Database Access: ").strip()
    password = getpass("Contraseña de Database Access (entrada oculta): ")
    uri = f"mongodb+srv://{host}/"

    client = MongoClient(
        uri,
        username=username,
        password=password,
        authSource="admin",
        tls=True,
        connectTimeoutMS=5000,
        serverSelectionTimeoutMS=8000,
        appname="BIMetrics-Atlas-Diagnostic",
    )
    try:
        client.admin.command("ping")
        print("RESULTADO: conexión y autenticación correctas.")
        return 0
    except PyMongoError as error:
        detail = str(error).split("Topology Description:")[0].strip()
        print(f"RESULTADO: {type(error).__name__}")
        print(detail[:1200])
        return 1
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
