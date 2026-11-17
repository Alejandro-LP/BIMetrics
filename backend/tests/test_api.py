"""Pruebas de la API. Ejecutar desde backend/:  python -m pytest -q"""
import os
import tempfile
from io import BytesIO
from unittest.mock import patch
from zipfile import ZipFile

import ifcopenshell

# La base de pruebas va en una carpeta temporal, nunca en data/
os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/prueba.db"

import pytest  # noqa: E402

from app import create_app  # noqa: E402
from app.services.usuarios_mongo import _coleccion  # noqa: E402
from sqlalchemy.exc import OperationalError  # noqa: E402


@pytest.fixture
def c():
    cliente = create_app().test_client()
    cliente.environ_base["HTTP_ORIGIN"] = "http://localhost:5173"
    usuario = cliente.post("/api/auth/registro", json={
        "nombre_completo": "Cuenta de pruebas",
        "email": "sesion@pruebas.local",
        "password": "ClaveDePrueba123",
        "rol": "arquitecto",
        "autoriza_datos": True,
    }).get_json()
    _coleccion().update_one({"id_usuario": usuario["id_usuario"]}, {"$set": {"rol": "administrador"}})
    return cliente


@pytest.fixture
def datos(c):
    u = c.post("/api/usuarios", json={"nombre_completo": "Ana", "email": "ana@ejemplo.com", "rol": "ingeniero", "password": "ContrasenaPrueba123"}).get_json()
    p = c.post("/api/proyectos", json={"nombre_obra": "Casa de prueba"}).get_json()
    ins = {}
    for n, u_, costo in [("Concreto", "m3", 485000), ("Acero", "varilla", 46500), ("Oficial", "jornal", 115000)]:
        ins[n] = c.post("/api/insumos", json={"nombre_insumo": n, "unidad_medida": u_, "costo_unitario": costo}).get_json()
    return {"proyecto": p["id_proyecto"], "insumos": ins}


def test_salud(c):
    assert c.get("/api/salud").get_json() == {"estado": "ok"}


def test_importar_cantidades_ifc_sin_generar_txt(c):
    partida = {"codigo": "MURO-IFC", "unidad": "m2", "descripcion": "Muro de concreto", "precio_defecto": 100}
    assert c.post("/api/partidas", json=partida).status_code == 201
    proyecto = c.post("/api/proyectos", json={"nombre_obra": "Obra IFC"}).get_json()
    presupuesto = c.post("/api/presupuestos", json={"id_proyecto": proyecto["id_proyecto"]}).get_json()
    base = f"/api/presupuestos/{presupuesto['id_presupuesto']}"

    modelo = ifcopenshell.file(schema="IFC4")
    mm2 = modelo.create_entity("IfcSIUnit", UnitType="AREAUNIT", Prefix="MILLI", Name="SQUARE_METRE")
    m2 = modelo.create_entity("IfcSIUnit", UnitType="AREAUNIT", Name="SQUARE_METRE")
    asignacion = modelo.create_entity("IfcUnitAssignment", Units=[mm2])
    modelo.create_entity("IfcProject", GlobalId=ifcopenshell.guid.new(), UnitsInContext=asignacion)
    for area, unidad in [(12_500_000.0, None), (2.5, m2)]:
        muro = modelo.create_entity("IfcWall", GlobalId=ifcopenshell.guid.new(), Name="Muro de concreto")
        neta = modelo.create_entity("IfcQuantityArea", Name="NetSideArea", AreaValue=area, Unit=unidad)
        bruta = modelo.create_entity("IfcQuantityArea", Name="GrossSideArea", AreaValue=20.0, Unit=m2)
        for nombre in ("Qto_WallBaseQuantities", "BaseQuantities"):
            conjunto = modelo.create_entity(
                "IfcElementQuantity", GlobalId=ifcopenshell.guid.new(), Name=nombre, Quantities=[neta, bruta],
            )
            modelo.create_entity(
                "IfcRelDefinesByProperties", GlobalId=ifcopenshell.guid.new(),
                RelatedObjects=[muro], RelatingPropertyDefinition=conjunto,
            )
    modelo.create_entity("IfcWall", GlobalId=ifcopenshell.guid.new(), Name="Muro sin cómputo")
    resultado = c.post(base + "/importar-ifc/analizar", data={
        "archivo": (BytesIO(modelo.to_string().encode()), "obra.ifc"),
        "medida": "area_neta",
    })
    assert resultado.status_code == 200, resultado.get_json()
    lectura = resultado.get_json()
    assert lectura["elementos_omitidos"] == 1
    assert lectura["total_filas"] == 1
    fila = lectura["filas"][0]
    assert fila["cantidad"] == pytest.approx(15)
    assert fila["unidad"] == "m²"
    assert fila["sugerencias"][0]["codigo"] == "MURO-IFC"
    assert c.get(base).get_json()["detalle"] == []
    agregado = c.post(base + "/partidas", json={"codigo": "MURO-IFC", "cantidad": fila["cantidad"]})
    assert agregado.get_json()["detalle"][0]["subtotal"] == 1500


def test_importar_tabla_pegada_respeta_decimal_con_tres_cifras(c):
    proyecto = c.post("/api/proyectos", json={"nombre_obra": "Tabla BIM"}).get_json()
    presupuesto = c.post("/api/presupuestos", json={"id_proyecto": proyecto["id_proyecto"]}).get_json()
    base = f"/api/presupuestos/{presupuesto['id_presupuesto']}"
    datos = {"software": "archicad", "texto": "Nombre\tCantidad\tUnidad\nMuro\t1,250\tm²", "separador_decimal": ","}
    assert c.post(base + "/importar-tabla/analizar", json=datos).get_json()["filas"][0]["cantidad"] == 1.25
    datos["texto"] = "Nombre\tCantidad\tUnidad\nMuro\t1.200,25 m2\tm²"
    assert c.post(base + "/importar-tabla/analizar", json=datos).get_json()["filas"][0]["cantidad"] == 1200.25
    assert c.post(base + "/importar-ifc/analizar", data={
        "archivo": (BytesIO(b"texto sin IFC"), "obra.ifc"), "medida": "longitud",
    }).status_code == 400


def test_invitaciones_para_cualquier_perfil_y_panel_admin(c):
    proyecto = c.post("/api/proyectos", json={"nombre_obra": "Obra compartida"}).get_json()
    id_proyecto = proyecto["id_proyecto"]
    ruta = f"/api/proyectos/{id_proyecto}/invitaciones"
    canje = "/api/proyectos/invitaciones/aceptar"

    for rol in ("arquitecto", "ingeniero", "cliente", "administrador"):
        invitado = c.application.test_client()
        invitado.environ_base["HTTP_ORIGIN"] = "http://localhost:5173"
        email = f"{rol}@pruebas.local"
        if rol == "administrador":
            assert c.post("/api/usuarios", json={
                "nombre_completo": "Administrador invitado", "email": email, "rol": rol,
                "password": "ClaveDePrueba123",
            }).status_code == 201
            assert invitado.post("/api/auth/login", json={"email": email, "password": "ClaveDePrueba123"}).status_code == 200
        else:
            assert invitado.post("/api/auth/registro", json={
                "nombre_completo": "Cuenta invitada", "email": email, "rol": rol,
                "password": "ClaveDePrueba123", "autoriza_datos": True,
            }).status_code == 201

        assert invitado.get("/api/proyectos").get_json() == []
        if rol == "cliente":
            restringida = c.post(ruta, json={"rol": "ingeniero"}).get_json()["codigo"]
            assert invitado.post(canje, json={"codigo": restringida}).status_code == 403
        creada = c.post(ruta, json={})
        assert creada.status_code == 201
        codigo = creada.get_json()["codigo"]
        assert c.post(canje, json={"codigo": codigo}).status_code == 400
        for _ in range(2):
            assert invitado.post(canje, json={"codigo": codigo}).status_code == 200
        assert invitado.get("/api/proyectos").get_json()[0]["id_proyecto"] == id_proyecto
        assert invitado.get("/api/auth/sesion").get_json()["rol"] == rol
        panel = invitado.get("/api/dashboard/administracion")
        assert panel.status_code == (200 if rol == "administrador" else 403)
        if rol == "cliente":
            assert invitado.post("/api/presupuestos", json={"id_proyecto": id_proyecto}).status_code == 403
        if rol == "administrador":
            assert panel.get_json()["proyectos_compartidos"] == 1
            assert panel.get_json()["cuentas_por_rol"]["administrador"] == 2


def test_restablecimiento_local_reemplaza_password_e_invalida_sesiones(c):
    c.application.config.update(PASSWORD_RESET_DEBUG=True, BIMETRICS_ENV="development", SMTP_HOST="")
    recuperacion = c.application.test_client()
    recuperacion.environ_base["HTTP_ORIGIN"] = "http://localhost:5173"
    datos = {"email": "sesion@pruebas.local"}
    solicitar = "/api/auth/solicitar-restablecimiento"
    restablecer = "/api/auth/restablecer-password"
    respuesta = recuperacion.post(solicitar, json=datos)
    assert respuesta.status_code == 200
    token = respuesta.get_json()["enlace_desarrollo"].split("token=")[1]
    assert "enlace_desarrollo" not in recuperacion.post(solicitar, json=datos).get_json()
    assert "enlace_desarrollo" not in recuperacion.post(solicitar, json={"email": "otra@pruebas.local"}).get_json()
    assert recuperacion.post(restablecer, json={"token": token, "password": "corta"}).status_code == 400
    nueva = {"token": token, "password": "ClaveRestablecida123!"}
    assert recuperacion.post(restablecer, json=nueva).status_code == 200
    assert recuperacion.post(restablecer, json=nueva).status_code == 400
    assert c.get("/api/auth/sesion").status_code == 401
    assert recuperacion.post("/api/auth/login", json={**datos, "password": "ClaveDePrueba123"}).status_code == 401
    assert recuperacion.post("/api/auth/login", json={**datos, "password": nueva["password"]}).status_code == 200


def test_restablecimiento_sin_smtp_reporta_indisponibilidad_a_todos(c):
    c.application.config.update(PASSWORD_RESET_DEBUG=True, BIMETRICS_ENV="production", SMTP_HOST="")
    ruta = "/api/auth/solicitar-restablecimiento"
    registrado = c.post(ruta, json={"email": "sesion@pruebas.local"})
    desconocido = c.post(ruta, json={"email": "otra@pruebas.local"})
    assert registrado.status_code == desconocido.status_code == 503
    assert registrado.get_json() == desconocido.get_json()


@pytest.mark.parametrize("ssl_directo,puerto", [(False, 587), (True, 465)])
def test_restablecimiento_envia_por_smtp_sin_exponer_token(c, ssl_directo, puerto):
    c.application.config.update(
        PASSWORD_RESET_DEBUG=True, BIMETRICS_ENV="production", APP_BASE_URL="https://bimetrics.test",
        SMTP_HOST="smtp.bimetrics.test", SMTP_FROM="cuentas@bimetrics.test",
        SMTP_PORT=puerto, SMTP_USE_SSL=ssl_directo, SMTP_USE_TLS=True,
        SMTP_USERNAME="mailer", SMTP_PASSWORD="clave-de-prueba",
    )
    transporte = "SMTP_SSL" if ssl_directo else "SMTP"
    with patch(f"app.services.correo.smtplib.{transporte}") as smtp:
        resultado = c.post("/api/auth/solicitar-restablecimiento", json={"email": "sesion@pruebas.local"})
        assert resultado.status_code == 200
        assert "enlace_desarrollo" not in resultado.get_json()
        conexion = smtp.return_value.__enter__.return_value
        assert conexion.starttls.called is (not ssl_directo)
        conexion.login.assert_called_once()
        mensaje = conexion.send_message.call_args.args[0]
        assert mensaje["To"] == "sesion@pruebas.local"
        enlace = next(palabra for palabra in mensaje.get_content().split() if palabra.startswith("https://"))
        assert enlace.startswith("https://bimetrics.test/restablecer?token=")
    token = enlace.split("token=")[1]
    assert c.post("/api/auth/restablecer-password", json={"token": token, "password": "NuevaClave123!"}).status_code == 200


def test_produccion_rechaza_cookie_insegura(monkeypatch):
    monkeypatch.setenv("BIMETRICS_ENV", "production")
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "0")
    with pytest.raises(RuntimeError, match="SESSION_COOKIE_SECURE=1"):
        create_app()


def test_cors_permite_frontend_con_sesion(c):
    response = c.get("/api/salud", headers={"Origin": "http://localhost:5173"})
    assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:5173"
    assert response.headers["Access-Control-Allow-Credentials"] == "true"


def test_origen_no_configurado_no_recibe_cors(c):
    response = c.get("/api/salud", headers={"Origin": "https://sitio-malicioso.example"})
    assert "Access-Control-Allow-Origin" not in response.headers


def test_registro_login_y_cookie_de_sesion(c):
    cliente = create_app().test_client()
    cliente.environ_base["HTTP_ORIGIN"] = "http://localhost:5173"
    datos = {
        "nombre_completo": "Usuario Auth",
        "email": "usuario.auth@pruebas.local",
        "password": "ClaveSegura123!",
        "rol": "cliente",
        "autoriza_datos": True,
    }
    registro = cliente.post("/api/auth/registro", json=datos)
    assert registro.status_code == 201
    assert registro.get_json()["rol"] == "cliente"
    cookie = registro.headers["Set-Cookie"]
    assert "HttpOnly" in cookie
    assert "SameSite=Lax" in cookie
    assert "Secure" not in cookie  # Vite de desarrollo se sirve por HTTP.
    assert cliente.get("/api/auth/sesion").get_json()["email"] == datos["email"]

    cliente.post("/api/auth/logout")
    acceso = cliente.post("/api/auth/login", json={"email": datos["email"], "password": datos["password"]})
    assert acceso.status_code == 200
    assert acceso.get_json()["email"] == datos["email"]
    assert cliente.get("/api/auth/sesion").status_code == 200


def test_auth_rechaza_datos_invalidos_y_origen_hostil(c):
    cliente = create_app().test_client()
    cliente.environ_base["HTTP_ORIGIN"] = "http://localhost:5173"
    assert cliente.post("/api/auth/registro", json={
        "nombre_completo": "Hacker", "email": "hacker@pruebas.local",
        "password": "ClaveSegura123!", "rol": "administrador", "autoriza_datos": True,
    }).status_code == 400
    assert cliente.post("/api/auth/login", json={
        "email": "' OR 1=1 --", "password": "incorrecta",
    }).status_code == 401
    rechazado = cliente.post("/api/auth/registro", json={
        "nombre_completo": "Hacker", "email": "hacker@pruebas.local",
        "password": "ClaveSegura123!", "rol": "cliente", "autoriza_datos": True,
    }, headers={"Origin": "https://sitio-malicioso.example"})
    assert rechazado.status_code == 403


def test_respuestas_api_incluyen_cabeceras_de_seguridad(c):
    response = c.get("/api/salud")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Cache-Control"] == "no-store"


def test_escrituras_rechazan_solicitudes_sin_origen(c):
    respuesta = c.post("/api/proyectos", json={"nombre_obra": "Sin origen"}, headers={"Origin": ""})
    assert respuesta.status_code == 403


def test_cliente_solo_puede_consultar(c, datos):
    cliente = create_app().test_client()
    cliente.environ_base["HTTP_ORIGIN"] = "http://localhost:5173"
    registro = cliente.post("/api/auth/registro", json={
        "nombre_completo": "Cliente", "email": "cliente@pruebas.local",
        "password": "ClaveSegura123!", "rol": "cliente", "autoriza_datos": True,
    })
    assert registro.status_code == 201
    assert cliente.get("/api/proyectos").status_code == 200
    assert cliente.post("/api/proyectos", json={"nombre_obra": "No permitido"}).status_code == 403


def test_usuario_admin_creado_tiene_hash_y_puede_iniciar_sesion(c):
    creado = c.post("/api/usuarios", json={
        "nombre_completo": "Cuenta gestionada", "email": "gestionada@pruebas.local",
        "rol": "cliente", "password": "ClaveGestionada123!",
    })
    assert creado.status_code == 201
    documento = _coleccion().find_one({"email": "gestionada@pruebas.local"})
    assert documento["password_hash"] != "ClaveGestionada123!"
    assert c.post("/api/auth/login", json={
        "email": "gestionada@pruebas.local", "password": "ClaveGestionada123!",
    }).status_code == 200
    assert c.post("/api/auth/login", json={
        "email": "sesion@pruebas.local", "password": "ClaveDePrueba123",
    }).status_code == 200
    perfil = c.get(f"/api/usuarios/{creado.get_json()['id_usuario']}")
    assert perfil.status_code == 200
    assert "password_hash" not in perfil.get_json()


def test_catalogo_maestro_crud_restringido_a_admin(c):
    datos = {
        "codigo": "QA-001",
        "unidad": "m2",
        "descripcion": "Partida de prueba de QA",
        "precio_defecto": 1250.5,
        "variaciones": [{"tipo": "acabado", "opcion": "mate", "precio": 1300, "es_defecto": True}],
    }
    creado = c.post("/api/partidas", json=datos)
    assert creado.status_code == 201
    assert creado.get_json()["variaciones"][0]["opcion"] == "mate"
    actualizado = c.put("/api/partidas/QA-001", json={**datos, "descripcion": "Partida actualizada"})
    assert actualizado.status_code == 200
    assert actualizado.get_json()["descripcion"] == "Partida actualizada"
    assert c.get("/api/partidas/QA-001").status_code == 200
    assert c.delete("/api/partidas/QA-001").status_code == 204

    cliente = create_app().test_client()
    cliente.environ_base["HTTP_ORIGIN"] = "http://localhost:5173"
    usuario = cliente.post("/api/auth/registro", json={
        "nombre_completo": "Cliente QA", "email": "catalogo.cliente@pruebas.local",
        "password": "ClaveSegura123!", "rol": "cliente", "autoriza_datos": True,
    })
    assert usuario.status_code == 201
    assert cliente.post("/api/partidas", json=datos).status_code == 403


def test_gestion_administrativa_de_roles_y_eliminacion(c):
    administrador = c.get("/api/auth/sesion").get_json()
    propia = f"/api/usuarios/{administrador['id_usuario']}"
    assert c.delete(propia).status_code == 409
    assert c.put(propia, json={**administrador, "rol": "cliente"}).status_code == 409

    datos = {"nombre_completo": "Otra administradora", "email": "otra.admin@pruebas.local",
             "password": "ClaveSegura123!", "rol": "administrador"}
    creado = c.post("/api/usuarios", json=datos)
    assert creado.status_code == 201
    ruta = f"/api/usuarios/{creado.get_json()['id_usuario']}"
    otra = c.application.test_client()
    otra.environ_base["HTTP_ORIGIN"] = "http://localhost:5173"
    login = {"email": datos["email"], "password": datos["password"]}
    assert otra.post("/api/auth/login", json=login).status_code == 200
    assert otra.get("/api/usuarios").status_code == 200
    assert c.put(ruta, json={**datos, "password": "", "rol": "ingeniero"}).status_code == 200
    assert otra.get("/api/auth/sesion").status_code == 401
    assert otra.post("/api/auth/login", json=login).status_code == 200
    assert otra.get("/api/usuarios").status_code == 403
    assert c.delete(ruta).status_code == 204
    assert otra.get("/api/auth/sesion").status_code == 401
    assert c.get(ruta).status_code == 404


def test_admin_no_elimina_al_propietario_de_otra_obra(c):
    datos = {"nombre_completo": "Propietario", "email": "propietario@pruebas.local",
             "password": "ClaveSegura123!", "rol": "ingeniero"}
    propietario = c.post("/api/usuarios", json=datos).get_json()
    otro = c.application.test_client()
    otro.environ_base["HTTP_ORIGIN"] = "http://localhost:5173"
    assert otro.post("/api/auth/login", json={"email": datos["email"], "password": datos["password"]}).status_code == 200
    assert otro.post("/api/proyectos", json={"nombre_obra": "Obra en curso"}).status_code == 201
    assert c.delete(f"/api/usuarios/{propietario['id_usuario']}").status_code == 409
    assert otro.get("/api/proyectos").get_json()[0]["nombre_obra"] == "Obra en curso"


def test_actualizar_precio_conserva_variaciones_y_presupuestos(c):
    datos = {"codigo": "PRECIO-QA", "unidad": "m", "descripcion": "Tubería QA", "precio_defecto": 100,
             "variaciones": [{"tipo": "material", "opcion": "PVC", "precio": 120}]}
    assert c.post("/api/partidas", json=datos).status_code == 201
    proyecto = c.post("/api/proyectos", json={"nombre_obra": "Obra QA"}).get_json()
    presupuesto = c.post("/api/presupuestos", json={"id_proyecto": proyecto["id_proyecto"]}).get_json()
    ruta = f"/api/presupuestos/{presupuesto['id_presupuesto']}"
    assert c.post(ruta + "/partidas", json={"codigo": datos["codigo"], "cantidad": 2}).status_code == 201

    precio = "/api/partidas/PRECIO-QA/precio"
    for invalido in ("-1", "NaN", "123.123", "1000000000000"):
        assert c.patch(precio, json={"precio_defecto": invalido}).status_code == 400
    assert c.patch(precio, json={"precio_defecto": "150.25"}).get_json()["precio_defecto"] == 150.25
    guardada = c.get("/api/partidas/PRECIO-QA").get_json()
    assert guardada["descripcion"] == datos["descripcion"]
    assert guardada["variaciones"][0]["precio"] == 120
    anterior = c.get(ruta).get_json()["detalle"][0]
    assert anterior["costo_unitario_aplicado"] == 100
    precio_ciudad = f"/api/insumos/{anterior['id_insumo']}/precio-ciudad"
    assert c.patch(precio_ciudad, json={"ciudad": "Bogotá", "costo_unitario": "180.25"}).status_code == 200
    assert c.post(ruta + "/partidas", json={"codigo": datos["codigo"], "cantidad": 2}).status_code == 201
    assert [item["costo_unitario_aplicado"] for item in c.get(ruta).get_json()["detalle"]] == [100, 180.25]

    proyecto_nuevo = c.post("/api/proyectos", json={"nombre_obra": "Obra en Medellín", "ciudad": "Medellín"}).get_json()
    nuevo = c.post("/api/presupuestos", json={"id_proyecto": proyecto_nuevo["id_proyecto"]}).get_json()
    incorporacion = c.post(f"/api/presupuestos/{nuevo['id_presupuesto']}/partidas", json={"codigo": datos["codigo"], "cantidad": 1})
    assert incorporacion.get_json()["detalle"][0]["costo_unitario_aplicado"] == 150.25

    otro = c.application.test_client()
    otro.environ_base["HTTP_ORIGIN"] = "http://localhost:5173"
    assert otro.post("/api/auth/registro", json={
        "nombre_completo": "Profesional", "email": "precio@pruebas.local", "rol": "ingeniero",
        "password": "ClaveSegura123!", "autoriza_datos": True,
    }).status_code == 201
    assert otro.patch(precio, json={"precio_defecto": "2"}).status_code == 403
    assert otro.patch(precio_ciudad, json={"ciudad": "Bogotá", "costo_unitario": "2"}).status_code == 403


def test_sql_no_disponible_responde_json_503(c):
    outage = OperationalError("SELECT 1", {}, RuntimeError("offline"))
    with patch("app.services.dashboard.operational_engine.connect", side_effect=outage):
        response = c.get("/api/dashboard/resumen")
    assert response.status_code == 503
    assert "error" in response.get_json()


def test_insumo_duplicado_da_409(c, datos):
    r = c.post("/api/insumos", json={"nombre_insumo": "Concreto", "unidad_medida": "m3", "costo_unitario": 1})
    assert r.status_code == 409


def test_validaciones(c, datos):
    assert c.post("/api/insumos", json={"nombre_insumo": "X"}).status_code == 400
    assert c.post("/api/usuarios", json={"nombre_completo": "B", "email": "b@e.co", "rol": "jefe"}).status_code == 400
    assert c.get("/api/presupuestos/99999").status_code == 404
    response = c.post("/api/presupuestos", json={
        "id_proyecto": datos["proyecto"],
        "detalle": [{"id_insumo": datos["insumos"]["Concreto"]["id_insumo"], "cantidad": float("nan")}],
    })
    assert response.status_code == 400


def test_presupuesto_calcula_total(c, datos):
    i = datos["insumos"]
    lineas = [{"id_insumo": i["Concreto"]["id_insumo"], "cantidad": 0.95},
              {"id_insumo": i["Acero"]["id_insumo"], "cantidad": 8},
              {"id_insumo": i["Oficial"]["id_insumo"], "cantidad": 2}]
    p = c.post("/api/presupuestos", json={"id_proyecto": datos["proyecto"], "detalle": lineas}).get_json()
    assert p["costo_total"] == 0.95 * 485000 + 8 * 46500 + 2 * 115000
    assert len(p["detalle"]) == 3
    assert c.post(f"/api/presupuestos/{p['id_presupuesto']}/calcular").get_json()["costo_total"] == p["costo_total"]


def test_aiu_se_aplica_al_costo_directo_y_se_puede_actualizar(c, datos):
    acero = datos["insumos"]["Acero"]["id_insumo"]
    creado = c.post("/api/presupuestos", json={
        "id_proyecto": datos["proyecto"],
        "detalle": [{"id_insumo": acero, "cantidad": 2}],
        "aiu": {"administracion": 5, "imprevistos": 2, "utilidad": 3},
    }).get_json()
    assert creado["costo_directo"] == 93000
    assert creado["valor_administracion"] == 4650
    assert creado["valor_imprevistos"] == 1860
    assert creado["valor_utilidad"] == 2790
    assert creado["costo_total"] == 102300

    actualizado = c.put(f"/api/presupuestos/{creado['id_presupuesto']}/aiu", json={
        "aiu": {"administracion": 10, "imprevistos": 0, "utilidad": 5},
    }).get_json()
    assert actualizado["costo_total"] == 106950
    assert c.put(f"/api/presupuestos/{creado['id_presupuesto']}/aiu", json={
        "aiu": {"administracion": -1},
    }).status_code == 400


def test_duplicar_usa_costos_vigentes(c, datos):
    i = datos["insumos"]["Acero"]
    p = c.post("/api/presupuestos", json={"id_proyecto": datos["proyecto"],
                                           "detalle": [{"id_insumo": i["id_insumo"], "cantidad": 10}]}).get_json()
    c.put(f"/api/insumos/{i['id_insumo']}", json={"nombre_insumo": "Acero", "unidad_medida": "varilla", "costo_unitario": 50000})
    copia = c.post(f"/api/presupuestos/{p['id_presupuesto']}/duplicar").get_json()
    assert p["costo_total"] == 465000       # el original conserva el costo con que se calculó
    assert copia["costo_total"] == 500000   # la copia toma el costo actual del catálogo


def test_capitulos_filtros_historial_y_duplicacion_a_obra_nueva(c, datos):
    proyecto = c.post("/api/proyectos", json={
        "nombre_obra": "Obra Demo",
        "ciudad": "Bogotá",
        "cliente": "Cliente Demo",
    }).get_json()
    acero = datos["insumos"]["Acero"]
    creado = c.post("/api/presupuestos", json={
        "id_proyecto": proyecto["id_proyecto"],
        "detalle": [{"id_insumo": acero["id_insumo"], "cantidad": 2, "capitulo": "Estructura"}],
    })
    assert creado.status_code == 201
    assert creado.get_json()["detalle"][0]["capitulo"] == "Estructura"

    nuevo = c.post(f"/api/presupuestos/{creado.get_json()['id_presupuesto']}/duplicar", json={
        "nuevo_proyecto": {"nombre_obra": "Obra duplicada", "ciudad": "Bogotá", "cliente": "Cliente Demo"},
    })
    assert nuevo.status_code == 201
    assert nuevo.get_json()["proyecto_nuevo"] is True
    assert nuevo.get_json()["detalle"][0]["capitulo"] == "Estructura"
    assert c.get(f"/api/proyectos/{proyecto['id_proyecto']}/presupuestos?desde=2099-01-01").get_json() == []
    filtrado = c.get(f"/api/proyectos/{proyecto['id_proyecto']}/presupuestos?cliente=Demo&desde=2000-01-01")
    assert filtrado.status_code == 200
    assert len(filtrado.get_json()) == 1
    assert c.get(f"/api/proyectos/{proyecto['id_proyecto']}/presupuestos?desde=2099-12-31&hasta=2000-01-01").status_code == 400


def test_insumo_se_puede_archivar_y_no_agregar_mas(c, datos):
    item = datos["insumos"]["Concreto"]
    presupuesto = c.post("/api/presupuestos", json={"id_proyecto": datos["proyecto"]}).get_json()
    archivado = c.patch(f"/api/insumos/{item['id_insumo']}/estado", json={"activo": False})
    assert archivado.status_code == 200
    assert archivado.get_json()["activo"] in (False, 0)
    assert all(row["id_insumo"] != item["id_insumo"] for row in c.get("/api/insumos").get_json())
    assert any(row["id_insumo"] == item["id_insumo"] for row in c.get("/api/insumos?incluir_inactivos=1").get_json())
    agregado = c.post(f"/api/presupuestos/{presupuesto['id_presupuesto']}/detalle", json={
        "id_insumo": item["id_insumo"], "cantidad": 1,
    })
    assert agregado.status_code == 400


def test_ajuste_masivo_de_precios_restringido(c, datos):
    concreto = datos["insumos"]["Concreto"]
    acero = datos["insumos"]["Acero"]
    c.post("/api/insumos", json={"nombre_insumo": "Concreto", "unidad_medida": "m3", "costo_unitario": 485000, "ciudad": "Bogotá"})
    c.post("/api/insumos", json={"nombre_insumo": "Acero", "unidad_medida": "varilla", "costo_unitario": 46500, "ciudad": "Bogotá"})
    response = c.put("/api/insumos/precios/ajuste-masivo", json={
        "ciudad": "Bogotá", "porcentaje": 10, "ids_insumos": [concreto["id_insumo"]],
    })
    assert response.status_code == 200
    assert response.get_json()["precios_actualizados"] == 1
    prices = {row["id_insumo"]: row["costo_unitario"] for row in c.get("/api/insumos?ciudad=Bogot%C3%A1").get_json()}
    assert float(prices[concreto["id_insumo"]]) == 533500
    assert float(prices[acero["id_insumo"]]) == 46500


def test_insumo_en_uso_no_se_borra(c, datos):
    id_insumo = datos["insumos"]["Concreto"]["id_insumo"]
    presupuesto = c.post("/api/presupuestos", json={
        "id_proyecto": datos["proyecto"],
        "detalle": [{"id_insumo": id_insumo, "cantidad": 1}],
    })
    assert presupuesto.status_code == 201
    assert c.delete(f"/api/insumos/{id_insumo}").status_code == 409


def test_descargas_pdf_y_word_requieren_sesion_y_generan_archivos(c, datos):
    presupuesto = c.post("/api/presupuestos", json={
        "id_proyecto": datos["proyecto"],
        "detalle": [{"id_insumo": datos["insumos"]["Acero"]["id_insumo"], "cantidad": 2}],
    })
    assert presupuesto.status_code == 201
    ruta = f"/api/presupuestos/{presupuesto.json['id_presupuesto']}"
    sin_sesion = create_app().test_client()

    for formato in ("pdf", "word"):
        assert sin_sesion.get(f"{ruta}/{formato}").status_code == 401

    pdf = c.get(f"{ruta}/pdf")
    assert pdf.status_code == 200
    assert pdf.mimetype == "application/pdf"
    assert pdf.data.startswith(b"%PDF-")
    assert "attachment" in pdf.headers["Content-Disposition"]

    word = c.get(f"{ruta}/word")
    assert word.status_code == 200
    assert word.mimetype == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    assert "attachment" in word.headers["Content-Disposition"]
    with ZipFile(BytesIO(word.data)) as archivo:
        assert "word/document.xml" in archivo.namelist()
