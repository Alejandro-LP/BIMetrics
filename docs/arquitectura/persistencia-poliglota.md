# Arquitectura de persistencia poliglota

## Alcance y estado verificado en el codigo

BIMetrics usa SQL para informacion transaccional del presupuesto y MongoDB para identidades, preferencias y actividad BIM. La identidad de una persona vive en MongoDB; SQL conserva el `id_usuario` como referencia logica en las filas de proyectos y colaboraciones. No existe una tabla SQL `USUARIOS` en el modelo actual.

| Almacen | Datos persistidos | Codigo de acceso |
|---|---|---|
| SQL operacional (SQLite local) | `PROYECTOS`, `PROYECTO_COLABORADORES`, `PRESUPUESTOS`, `DETALLE_PRESUPUESTO`, `INSUMOS`, `PRECIOS_CIUDAD` | `backend/app/models.py`, `backend/app/services/` y `operational_engine` |
| SQL del catalogo (MySQL por defecto) | `partidas`, `variaciones_opciones` | `backend/app/catalog_models.py`, Flask-SQLAlchemy y `partida_service.py` |
| MongoDB `bimetrics_users` | Colecciones `usuarios` y `contadores` | `usuarios_mongo.py`, PyMongo |
| MongoDB `bimetrics_nosql` | Coleccion `actividades_bim` | `actividades_bim.py`, PyMongo |

La configuracion de despliegue esta separada en `OPERATIONAL_DATABASE_URL`, `CATALOG_DATABASE_URL` y `MONGO_URI`. El motor operacional rechaza una URL MySQL deliberadamente; el catalogo relacional es un segundo almacen SQL, no una coleccion documental.

## Por que usar documentos para la actividad BIM

El historial de importaciones desde Revit y Archicad contiene atributos que cambian segun software, version, categoria y validaciones. Un modelo puede incluir cantidades y volumenes; otro, advertencias, elementos omitidos y propiedades propias de la herramienta. Guardar ese payload variable en una tabla rigida obliga a alterar el esquema con cada nueva forma de metadatos.

MongoDB guarda un nucleo comun para filtrar y ordenar eventos y un objeto `detalles_bim` para el contenido variable. El historial crece por evento y se consulta ordenado por usuario y fecha, para lo cual existe un indice compuesto. SQL mantiene los presupuestos, cantidades, precios y relaciones donde se requieren restricciones y transacciones.

### Documento representativo

```json
{
  "_id": "ObjectId generado por MongoDB",
  "id_usuario": 42,
  "id_proyecto": 18,
  "tipo_evento": "importacion_revit_txt",
  "software_origen": "Autodesk Revit 2024",
  "nombre_archivo": "Computos_Estructurales.txt",
  "estado": "advertencia",
  "detalles_bim": {
    "num_elementos": 42,
    "volumen_total_m3": 18.75,
    "advertencias": ["Elemento sin longitud explicita"],
    "propiedades_origen": {"disciplina": "Estructuras"}
  },
  "fecha_registro": "fecha UTC",
  "fecha_actualizacion": "fecha UTC"
}
```

Los campos `id_usuario` e `id_proyecto` son referencias logicas entre motores: no hay transaccion distribuida ni clave foranea Mongo/SQL. La API valida que el usuario exista en MongoDB y, si se asocia una actividad con una obra, que la obra SQL pertenezca al usuario o este compartida con el. `detalles_bim` acepta solo objeto JSON y tiene un limite de 1 MB; los estados permitidos son `completado`, `advertencia` y `fallido`.

El documento de usuario se mantiene en `bimetrics_users.usuarios`. Incluye hash de contrasena (nunca la contrasena original), rol, consentimiento, fechas y preferencias flexibles. Los indices unicos de `id_usuario` y `email` protegen las identidades; el contador asigna identificadores enteros usados como referencias logicas por SQL.

## Persistencia poliglota en la aplicacion

`GET /api/dashboard/resumen` consulta en SQL las obras accesibles, el ultimo presupuesto por obra y el total de insumos. Luego consulta en MongoDB el perfil autenticado y la ultima actividad BIM. La respuesta contiene `usuario` y `resumen`, incluido `ultima_actividad_bim` y el indicador `mongodb_disponible`. Si MongoDB no responde, el resumen puede seguir devolviendo las metricas SQL y senala la indisponibilidad documental.

`GET /api/actividades-bim/usuario/<id>` combina el perfil y las actividades recientes, ambos almacenados en MongoDB. No es el endpoint SQL+NoSQL principal; para demostrar persistencia poliglota en una sola respuesta se debe usar `/api/dashboard/resumen`.

## CRUD documental y autorizacion

| Operacion | Endpoint | Efecto |
|---|---|---|
| Crear | `POST /api/actividades-bim` | Inserta una actividad del usuario autenticado en MongoDB |
| Leer una | `GET /api/actividades-bim/<id>` | Devuelve una actividad propia; administrador puede consultar otras |
| Listar | `GET /api/actividades-bim/usuario/<id>?limite=10` | Devuelve historial propio; administrador puede consultar otro perfil |
| Actualizar | `PUT /api/actividades-bim/<id>` | Actualiza campos permitidos de una actividad propia |
| Eliminar | `DELETE /api/actividades-bim/<id>` | Elimina una actividad propia |

El CRUD restringe las modificaciones a campos del contrato, protege el propietario mediante un filtro Mongo en la escritura/eliminacion y rechaza IDs y estados invalidos. El acceso a la API se controla con sesion. Los errores de MongoDB se responden con estado HTTP 503 sin exponer URI ni credenciales.

## Configuracion segura

Configura las variables en `.env`, que esta excluido de Git. No pegues credenciales en el repositorio ni en capturas compartidas.

```dotenv
SECRET_KEY=clave-aleatoria-local
SESSION_COOKIE_SECURE=0
OPERATIONAL_DATABASE_URL=sqlite:///data/presupuestos.db
CATALOG_DATABASE_URL=mysql+pymysql://usuario:clave@localhost/BIMetricsBD?charset=utf8mb4
MONGO_URI=mongodb+srv://usuario:clave@cluster.example.mongodb.net/
MONGO_DB_NAME=bimetrics_users
MONGO_ACTIVITY_DB_NAME=bimetrics_nosql
```

En produccion, usa una clave secreta aleatoria, HTTPS y `SESSION_COOKIE_SECURE=1`; limita la lista de IP en Atlas al origen del servidor. PyMongo comparte un `MongoClient` por proceso, usa TLS por defecto para URI Atlas `mongodb+srv` y aplica tiempos de conexion acotados. El endpoint publico `GET /api/salud/mongodb` ejecuta `ping`; una aplicacion iniciada no se considera prueba de que MongoDB este disponible.

## Flujo reproducible de evidencia

Inicia la API desde `backend/` y crea/inicia sesion con una cuenta de prueba. Los comandos siguientes generan una evidencia real al ejecutarse; reemplaza el correo y la contrasena por credenciales de prueba locales, nunca por credenciales compartidas:

```powershell
$base = 'http://127.0.0.1:5000'
$sesion = New-Object Microsoft.PowerShell.Commands.WebRequestSession
Invoke-RestMethod "$base/api/auth/login" -Method Post -WebSession $sesion `
  -ContentType 'application/json' `
  -Body '{"email":"cuenta-prueba@example.test","password":"contraseña-local"}'

# Comprueba conexion MongoDB sin revelar la URI.
Invoke-RestMethod "$base/api/salud/mongodb"

# Demuestra una respuesta combinada: metricas SQL y actividad/identidad MongoDB.
Invoke-RestMethod "$base/api/dashboard/resumen" -WebSession $sesion | ConvertTo-Json -Depth 8

# Registra una actividad del usuario autenticado; el ID se obtiene de la sesion.
$actividad = Invoke-RestMethod "$base/api/auth/sesion" -WebSession $sesion
$payload = @{
  id_usuario = $actividad.id_usuario
  tipo_evento = 'importacion_revit_txt'
  software_origen = 'Autodesk Revit 2024'
  nombre_archivo = 'modelo-prueba.txt'
  estado = 'completado'
  detalles_bim = @{ num_elementos = 42; advertencias = @() }
} | ConvertTo-Json -Depth 8
$creada = Invoke-RestMethod "$base/api/actividades-bim" -Method Post -WebSession $sesion `
  -ContentType 'application/json' -Body $payload

# Lee, modifica y elimina el documento creado.
Invoke-RestMethod "$base/api/actividades-bim/$($creada.id)" -WebSession $sesion
Invoke-RestMethod "$base/api/actividades-bim/$($creada.id)" -Method Put -WebSession $sesion `
  -ContentType 'application/json' -Body '{"estado":"advertencia","detalles_bim":{"revisado":true}}'
Invoke-RestMethod "$base/api/actividades-bim/$($creada.id)" -Method Delete -WebSession $sesion
```

Las pruebas automatizadas usan MongoDB simulado y SQLite temporales para que sean repetibles y no dependan de Atlas ni MySQL. Sus resultados no sustituyen una captura de una ejecucion contra servicios reales. Para la entrega final, conserva capturas de `/api/salud/mongodb`, del documento en Atlas Data Explorer y de `/api/dashboard/resumen` con datos de prueba; oculta correo, URI, IDs sensibles y cualquier secreto.

## Referencias de implementacion

- Configuracion y conexiones: `backend/app/config.py`, `backend/app/database.py`, `backend/app/extensions.py`.
- Modelo relacional: `backend/app/models.py`, `backend/app/catalog_models.py`.
- Identidades MongoDB: `backend/app/services/usuarios_mongo.py`.
- CRUD de actividades: `backend/app/services/actividades_bim.py`, `backend/app/services/actividades_bim_api.py`, `backend/app/routes/actividades_bim.py`.
- Endpoint combinado SQL + MongoDB: `backend/app/services/dashboard.py`, `backend/app/routes/dashboard.py`.
- Pruebas aisladas: `backend/tests/conftest.py`, `backend/tests/test_actividades_bim.py`.
