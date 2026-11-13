"""Casos de uso y persistencia de proyectos y colaboradores."""

import hashlib
import secrets
from datetime import datetime, timedelta

from sqlalchemy import text

from ..database import operational_engine
from ..errors import ErrorApi
from ..utils import filas, obtener
from .usuarios_mongo import obtener_usuario, obtener_usuario_por_email, obtener_usuarios


def listar_proyectos(id_usuario):
    """Lista proyectos propios y compartidos con el usuario."""
    consulta = text(
        "SELECT p.*, "
        "CASE WHEN p.id_usuario=:id THEN 1 ELSE 0 END AS es_propietario "
        "FROM PROYECTOS p "
        "WHERE p.id_usuario=:id OR EXISTS (SELECT 1 FROM PROYECTO_COLABORADORES c "
        "WHERE c.id_proyecto=p.id_proyecto AND c.id_usuario=:id) ORDER BY p.nombre_obra"
    )
    with operational_engine.connect() as connection:
        proyectos = filas(connection.execute(consulta, {"id": id_usuario}))
    usuarios = obtener_usuarios(proyecto["id_usuario"] for proyecto in proyectos)
    for proyecto in proyectos:
        responsable = usuarios.get(proyecto["id_usuario"])
        proyecto["responsable"] = responsable["nombre_completo"] if responsable else None
    return proyectos


def crear_proyecto(id_usuario, datos):
    """Valida y crea un proyecto propiedad del usuario."""
    nombre = datos.get("nombre_obra")
    ciudad = datos.get("ciudad", "Bogotá")
    cliente = datos.get("cliente")
    if not isinstance(nombre, str) or not nombre.strip() or len(nombre.strip()) > 150:
        raise ErrorApi(400, "El nombre debe tener entre 1 y 150 caracteres")
    if not isinstance(ciudad, str) or not ciudad.strip() or len(ciudad.strip()) > 100:
        raise ErrorApi(400, "La ciudad debe tener entre 1 y 100 caracteres")
    if cliente is not None and (not isinstance(cliente, str) or len(cliente.strip()) > 150):
        raise ErrorApi(400, "El nombre del cliente no es válido")

    with operational_engine.begin() as connection:
        resultado = connection.execute(
            text("INSERT INTO PROYECTOS (id_usuario, nombre_obra, cliente, ciudad) "
                 "VALUES (:usuario, :nombre, :cliente, :ciudad)"),
            {
                "usuario": id_usuario,
                "nombre": nombre.strip(),
                "cliente": cliente.strip() if cliente and cliente.strip() else None,
                "ciudad": ciudad.strip(),
            },
        )
        return obtener(connection, "PROYECTOS", "id_proyecto", resultado.lastrowid)


def obtener_historial_proyecto(id_proyecto, id_usuario, cliente="", desde=None, hasta=None):
    """Devuelve historial accesible con filtros opcionales de cliente y fecha."""
    with operational_engine.connect() as connection:
        acceso = connection.execute(
            text("SELECT 1 FROM PROYECTOS p WHERE p.id_proyecto=:proyecto AND "
                 "(p.id_usuario=:usuario OR EXISTS (SELECT 1 FROM PROYECTO_COLABORADORES c "
                 "WHERE c.id_proyecto=p.id_proyecto AND c.id_usuario=:usuario))"),
            {"proyecto": id_proyecto, "usuario": id_usuario},
        ).first()
        if not acceso:
            raise ErrorApi(404, "El proyecto no existe")
        resultado = connection.execute(
            text("SELECT b.*, p.nombre_obra, p.cliente, p.ciudad FROM PRESUPUESTOS b "
                 "JOIN PROYECTOS p ON p.id_proyecto=b.id_proyecto "
                 "WHERE b.id_proyecto=:proyecto "
                 "AND (:cliente='' OR LOWER(COALESCE(p.cliente,'')) LIKE :cliente) "
                 "AND (:desde IS NULL OR b.fecha_calculo>=:desde) "
                 "AND (:hasta IS NULL OR b.fecha_calculo<=:hasta) "
                 "ORDER BY b.fecha_calculo DESC, b.id_presupuesto DESC"),
            {"proyecto": id_proyecto, "cliente": f"%{cliente.strip().lower()}%", "desde": desde, "hasta": hasta},
        )
        return filas(resultado)


def invitar_colaborador(id_proyecto, id_propietario, email):
    """Agrega a un profesional al proyecto, solo por solicitud del propietario."""
    email = email.strip().lower() if isinstance(email, str) else ""
    if not email:
        raise ErrorApi(400, "Escribe el correo de la persona colaboradora")
    with operational_engine.begin() as connection:
        proyecto = connection.execute(
            text("SELECT 1 FROM PROYECTOS WHERE id_proyecto=:proyecto AND id_usuario=:usuario"),
            {"proyecto": id_proyecto, "usuario": id_propietario},
        ).first()
        if not proyecto:
            raise ErrorApi(404, "El proyecto no existe o no eres su propietario")
        usuario = obtener_usuario_por_email(email)
        if not usuario:
            raise ErrorApi(404, "No hay una cuenta registrada con ese correo")
        if usuario["rol"] not in ("arquitecto", "ingeniero"):
            raise ErrorApi(400, "Solo se puede invitar a un arquitecto o ingeniero")
        if usuario["id_usuario"] == id_propietario:
            raise ErrorApi(400, "Ya eres propietario de este proyecto")

        ya_colaborador = connection.execute(
            text("SELECT 1 FROM PROYECTO_COLABORADORES WHERE id_proyecto=:proyecto AND id_usuario=:usuario"),
            {"proyecto": id_proyecto, "usuario": usuario["id_usuario"]},
        ).first()
        if not ya_colaborador:
            connection.execute(
                text("INSERT INTO PROYECTO_COLABORADORES (id_proyecto, id_usuario, invitado_por) "
                     "VALUES (:proyecto, :usuario, :propietario)"),
                {"proyecto": id_proyecto, "usuario": usuario["id_usuario"], "propietario": id_propietario},
            )


def crear_codigo_invitacion(id_proyecto, id_propietario, rol):
    """Genera un código aleatorio, ligado a rol y proyecto, válido por siete días."""
    if rol not in ("arquitecto", "ingeniero", "cliente"):
        raise ErrorApi(400, "El código debe asignarse a un arquitecto, ingeniero o cliente")
    codigo = secrets.token_urlsafe(24)
    ahora = datetime.utcnow()
    expira = ahora + timedelta(days=7)
    with operational_engine.begin() as connection:
        proyecto = connection.execute(
            text("SELECT id_proyecto FROM PROYECTOS WHERE id_proyecto=:proyecto AND id_usuario=:usuario"),
            {"proyecto": id_proyecto, "usuario": id_propietario},
        ).first()
        if not proyecto:
            raise ErrorApi(404, "El proyecto no existe o no eres su creador")
        connection.execute(
            text(
                "INSERT INTO PROYECTO_INVITACIONES "
                "(id_proyecto, codigo_hash, rol, creado_por, creado_en, expira_en) "
                "VALUES (:proyecto, :hash, :rol, :usuario, :creado, :expira)"
            ),
            {
                "proyecto": id_proyecto,
                "hash": hashlib.sha256(codigo.encode("utf-8")).hexdigest(),
                "rol": rol,
                "usuario": id_propietario,
                "creado": ahora,
                "expira": expira,
            },
        )
    return {"codigo": codigo, "rol": rol, "expira_en": expira.isoformat() + "Z"}


def aceptar_codigo_invitacion(id_usuario, codigo):
    """Consume un código de un solo uso y agrega al usuario al proyecto asociado."""
    if not isinstance(codigo, str) or not 20 <= len(codigo.strip()) <= 100:
        raise ErrorApi(400, "El código no es válido o ya expiró")
    codigo_hash = hashlib.sha256(codigo.strip().encode("utf-8")).hexdigest()
    ahora = datetime.utcnow()
    with operational_engine.begin() as connection:
        invitacion = connection.execute(
            text(
                "SELECT id_invitacion, id_proyecto, rol, expira_en, aceptado_en "
                "FROM PROYECTO_INVITACIONES WHERE codigo_hash=:hash"
            ),
            {"hash": codigo_hash},
        ).mappings().first()
        if not invitacion or invitacion["aceptado_en"] is not None or invitacion["expira_en"] <= ahora:
            raise ErrorApi(400, "El código no es válido o ya expiró")
        perfil = obtener_usuario(id_usuario)
        if not perfil or perfil["rol"] != invitacion["rol"]:
            raise ErrorApi(403, "Este código fue creado para otro tipo de cuenta")
        propietario = connection.execute(
            text("SELECT id_usuario FROM PROYECTOS WHERE id_proyecto=:proyecto"),
            {"proyecto": invitacion["id_proyecto"]},
        ).scalar()
        if id_usuario == propietario:
            raise ErrorApi(400, "Ya eres propietario de este proyecto")
        existente = connection.execute(
            text("SELECT 1 FROM PROYECTO_COLABORADORES WHERE id_proyecto=:proyecto AND id_usuario=:usuario"),
            {"proyecto": invitacion["id_proyecto"], "usuario": id_usuario},
        ).first()
        if existente:
            raise ErrorApi(409, "Ya tienes acceso a este proyecto")
        reserva = connection.execute(
            text(
                "UPDATE PROYECTO_INVITACIONES SET aceptado_por=:usuario, aceptado_en=:ahora "
                "WHERE id_invitacion=:id AND aceptado_en IS NULL AND expira_en>:ahora"
            ),
            {"usuario": id_usuario, "ahora": ahora, "id": invitacion["id_invitacion"]},
        )
        if reserva.rowcount != 1:
            raise ErrorApi(400, "El código no es válido o ya expiró")
        connection.execute(
            text(
                "INSERT INTO PROYECTO_COLABORADORES (id_proyecto, id_usuario, invitado_por) "
                "SELECT id_proyecto, :usuario, creado_por FROM PROYECTO_INVITACIONES WHERE id_invitacion=:id"
            ),
            {"usuario": id_usuario, "id": invitacion["id_invitacion"]},
        )
        proyecto = connection.execute(
            text("SELECT id_proyecto, nombre_obra FROM PROYECTOS WHERE id_proyecto=:proyecto"),
            {"proyecto": invitacion["id_proyecto"]},
        ).mappings().first()
    return dict(proyecto)


def eliminar_proyecto(id_proyecto, id_propietario):
    """Elimina el proyecto propio y sus filas dependientes en orden seguro."""
    with operational_engine.begin() as connection:
        proyecto = connection.execute(
            text("SELECT 1 FROM PROYECTOS WHERE id_proyecto=:proyecto AND id_usuario=:usuario"),
            {"proyecto": id_proyecto, "usuario": id_propietario},
        ).first()
        if not proyecto:
            raise ErrorApi(404, "El proyecto no existe")
        connection.execute(
            text("DELETE FROM DETALLE_PRESUPUESTO WHERE id_presupuesto IN "
                 "(SELECT id_presupuesto FROM PRESUPUESTOS WHERE id_proyecto=:proyecto)"),
            {"proyecto": id_proyecto},
        )
        connection.execute(text("DELETE FROM PRESUPUESTOS WHERE id_proyecto=:proyecto"), {"proyecto": id_proyecto})
        connection.execute(text("DELETE FROM PROYECTO_COLABORADORES WHERE id_proyecto=:proyecto"), {"proyecto": id_proyecto})
        connection.execute(
            text("DELETE FROM PROYECTOS WHERE id_proyecto=:proyecto AND id_usuario=:usuario"),
            {"proyecto": id_proyecto, "usuario": id_propietario},
        )
