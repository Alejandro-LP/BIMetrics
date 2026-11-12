# BIMetrics

Aplicación web para gestionar proyectos y presupuestos de obra, consultar un catálogo de insumos y registrar actividad BIM. El sistema combina persistencia relacional (SQL) con almacenamiento documental (MongoDB).

## Contenido

- [Paquete de entrega académica](#paquete-de-entrega-académica)
- [Ruta de evaluación desde un clon limpio](#ruta-de-evaluación-desde-un-clon-limpio)
- [Guion de demostración para el docente](#guion-de-demostración-para-el-docente)
- [Características](#características)
- [Arquitectura](#arquitectura)
- [Requisitos](#requisitos)
- [Configuración](#configuración)
- [Ejecución](#ejecución)
- [Persistencia y datos](#persistencia-y-datos)
- [API principal](#api-principal)
- [Pruebas y calidad](#pruebas-y-calidad)
- [Solución de problemas](#solución-de-problemas)
- [Documentación](#documentación)

## Paquete de entrega académica

- [Entrega 3 · SRS de seguridad, autenticación y cierre (PDF)](docs/entrega-3/entrega-3-seguridad-y-api.pdf)
- [Entrega 2 · Persistencia políglota y verificación (PDF)](docs/entrega-3/entrega-2-persistencia-poliglota.pdf)
- [Trazabilidad de las entregas 1 y 2](docs/entrega-3/README.md)
- [Diagrama UML](docs/entrega-3/casos-de-uso.svg) y [contrato OpenAPI](docs/api/openapi.yaml)
- [Capturas, resultados y evidencia de conexión real a Atlas](docs/entrega-3/evidencias/README.md)

## Ruta de evaluación desde un clon limpio

1. Clona la rama de entrega y entra en la carpeta.
2. Instala Python y Node en las versiones de [Requisitos](#requisitos). Crea el entorno e instala las dependencias.
3. Escoge entre Atlas con MySQL y el modo de demostración con Docker Desktop.
4. Inicia la app. Abre **http://localhost:5173** y mantén abierta la terminal. Flask atiende en **http://127.0.0.1:5000**.
5. Comprueba los servicios. Si MongoDB devuelve HTTP 503, el registro y el inicio de sesión pueden fallar aunque la interfaz esté disponible.

~~~powershell
git clone --branch codex/entrega-3-seguridad-evidencias https://github.com/Alejandro-LP/BIMetrics.git
Set-Location BIMetrics
uv venv --python 3.14.2 .venv
uv pip install --python .venv\Scripts\python.exe -r backend\requirements.txt
npm --prefix frontend-bimetrics ci
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
~~~

### Ejecución con Atlas y MySQL

1. En Atlas, verifica que el clúster esté activo. Autoriza la IP de salida del equipo en **Database & Network Access** y configura un usuario de base de datos con acceso a los dominios de usuarios y actividad de BIMetrics.
2. En el archivo privado **.env**, define **SECRET_KEY**, **MONGO_URI** y las bases de usuarios y actividad BIM. Usa la cadena que Atlas genera para PyMongo.
3. En MySQL, crea el esquema que configuraste en **CATALOG_DATABASE_URL**. Restaura **data/catalogo/catalogo_precios_colombia.sql** o usa el importador que se describe en [Catálogo de insumos](#catálogo-de-insumos).
4. Desde la raíz, ejecuta **.\.venv\Scripts\python.exe start.py**. En desarrollo HTTP, usa **SESSION_COOKIE_SECURE=0**. Para producción, configura HTTPS y **SESSION_COOKIE_SECURE=1**.

### Ejecución independiente con Docker Desktop

En un clon de evaluación, configura **SECRET_KEY** en **.env** y usa una base operativa SQLite propia del clon. Si el clon ya contiene datos de trabajo, apunta **OPERATIONAL_DATABASE_URL** a un archivo separado. Con Docker Desktop iniciado, ejecuta **.\start_local.ps1**. Este modo inicia MongoDB local y usa un catálogo SQLite local. Registra cuentas nuevas de prueba en ese entorno. Para mostrar partidas del catálogo en esta modalidad, usa un catálogo local preparado o crea una partida de prueba por API con una cuenta administradora.

### Comprobaciones antes de la exposición

~~~powershell
$api = 'http://127.0.0.1:5000/api'
Invoke-RestMethod "$api/salud"
Invoke-RestMethod "$api/salud/mongodb"
~~~

Un HTTP 200 en salud general confirma que Flask responde. MongoDB se comprueba mediante ping. Para revisar SQL, inicia sesión y consulta **GET /api/partidas?limit=1** con la cookie. Si la lista está vacía, carga el catálogo o prepara una partida de prueba antes de la demostración.

## Guion de demostración para el docente

Usa cuentas y datos de prueba. Registra una cuenta de arquitectura para crear el presupuesto y una cuenta de cliente para comprobar la restricción de escritura. La cuenta administradora debe estar preparada por el responsable del entorno. El registro público admite arquitectura, ingeniería y cliente.

| Caso | Acción | Resultado esperado |
| --- | --- | --- |
| Seguridad | Consulta proyectos sin sesión. Inicia sesión como cliente e intenta modificar el catálogo por API. | HTTP 401 sin sesión y HTTP 403 para la escritura del cliente. |
| CU-01 · Catálogo | Como administrador, crea, consulta y edita una partida en **/api/partidas**. Elimina una partida desechable. | HTTP 201, 200, 200 y 204. |
| CU-02 · Cálculo | Agrega 20 m de una partida de $45.000 COP/m. Aplica 10 % de administración, 3 % de imprevistos y 7 % de utilidad. | Costo directo de $900.000, AIU de $180.000 y total de $1.080.000 COP. Valores ilustrativos. |
| CU-03 · Documentos | Descarga PDF, Word y Excel desde el presupuesto y abre los archivos. | Los tres formatos se descargan y muestran el desglose. |
| CU-04 · Historial | Duplica un presupuesto y consulta el historial del proyecto. | El historial muestra el original y su copia. La copia usa precios vigentes del destino. |
| Entrega 2 · SQL y NoSQL | Registra una actividad BIM vinculada a la obra. Consulta **GET /api/dashboard/resumen**. Después edita y elimina la actividad. | El resumen combina métricas SQL y actividad BIM. La lectura posterior a eliminar devuelve HTTP 404. |

La [trazabilidad](docs/entrega-3/README.md) distingue lo demostrado de los pasos originales pendientes, como capítulos constructivos, firma digital certificada y filtros por cliente o fecha.

### Cómo probar una ruta protegida

En PowerShell 7, conserva la cookie en la misma sesión. El encabezado **Origin** de las escrituras debe coincidir con el frontend configurado.

~~~powershell
$api = 'http://127.0.0.1:5000/api'
$origin = @{ Origin = 'http://localhost:5173' }
$email = Read-Host 'Correo de la cuenta de prueba'
$clave = Read-Host 'Contraseña de la cuenta de prueba' -MaskInput
$body = @{ email = $email; password = $clave } | ConvertTo-Json -Compress
Invoke-RestMethod "$api/auth/login" -Method Post -Headers $origin -ContentType 'application/json' -Body $body -SessionVariable sesion
Remove-Variable clave,body
Invoke-RestMethod "$api/auth/sesion" -WebSession $sesion
Invoke-RestMethod "$api/proyectos" -WebSession $sesion
Invoke-RestMethod "$api/partidas?limit=1" -WebSession $sesion
Invoke-RestMethod "$api/dashboard/resumen" -WebSession $sesion
~~~

- **401** indica sesión ausente, vencida o credenciales rechazadas.
- **403** indica permiso insuficiente u origen de escritura no autorizado.
- **404** indica recurso inexistente o fuera del alcance de la cuenta.
- **503** indica una dependencia no disponible.
- Para revisar los campos y respuestas de cada operación, consulta [OpenAPI](docs/api/openapi.yaml).

### Cómo leer las evidencias

- **Atlas en vivo.** La [respuesta de salud](docs/entrega-3/evidencias/atlas-en-vivo.json) confirma HTTP 200 del clúster real. El inicio de sesión con credenciales ficticias devolvió HTTP 401, el resultado esperado.
- **Pruebas reproducibles.** Pasaron **31 pruebas** del backend en el cierre. Se ejecutaron con SQLite en memoria y MongoDB simulado para aislar las reglas, los permisos y las exportaciones.
- **Interfaz y API.** El [índice de evidencias](docs/entrega-3/evidencias/README.md) identifica el entorno de cada captura y respuesta JSON.

## Características

- Administración de proyectos, presupuestos e insumos.
- Catálogo SQL de partidas, variaciones y precios de referencia.
- Sugerencias de mano de obra para cada partida: reglas por actividad y recomendación general de oficial y ayudante cuando no hay una regla específica. Los recursos con tarifa local se agregan al presupuesto; las partidas de alquiler de equipo con un montaje explícito asociado enlazan ambas actividades.
- Registro de usuarios, preferencias y actividad BIM.
- Dashboard que reúne información SQL y MongoDB.
- Los conteos del dashboard salen de las tablas SQL de partidas y variaciones; si MySQL no responde, usa los conteos del CSV local y señala que son una copia de respaldo.
- Validación de acceso a proyectos y propiedad de las actividades.

## Arquitectura

| Componente | Tecnología | Responsabilidad |
|---|---|---|
| Frontend | React, Vite | Interfaz de usuario |
| Backend | Python, Flask | API REST y lógica de negocio |
| SQL operacional | SQLite por defecto | Proyectos, presupuestos e insumos |
| SQL de catálogo | MySQL | Partidas y variaciones del catálogo maestro |
| NoSQL documental | MongoDB | Usuarios, preferencias y actividad BIM |

```mermaid
flowchart LR
    UI[React + Vite] --> API[API Flask]
    API --> SQL[(SQL operacional<br/>SQLite)]
    API --> CAT[(SQL catálogo<br/>MySQL)]
    API --> MONGO[(MongoDB<br/>usuarios y actividad BIM)]
```

La API coordina las consultas entre motores. Las relaciones entre SQL y MongoDB se establecen mediante identificadores lógicos, como `id_usuario` e `id_proyecto`; no hay una transacción distribuida entre ambos motores.

## Requisitos

- Python **3.14.2** (versión indicada en `.python-version`).
- Node.js **24.13.0** y npm (versión indicada en `.nvmrc`).
- [uv](https://docs.astral.sh/uv/) para crear e instalar el entorno Python.
- MongoDB accesible para autenticación, perfiles y actividades BIM.
- MySQL accesible para el catálogo maestro, salvo que uses el modo local descrito más abajo.

SQLite se utiliza por defecto para los datos operativos. MongoDB y MySQL pueden ser locales o servicios administrados.

## Configuración

### 1. Preparar el entorno

Ejecuta estos comandos desde la raíz del repositorio en PowerShell:

```powershell
uv venv --python 3.14.2 .venv
uv pip install --python .venv\Scripts\python.exe -r backend\requirements.txt
Copy-Item .env.example .env
npm --prefix frontend-bimetrics install
```

Si no tienes `uv`, puedes crear el entorno con `python -m venv .venv` y luego instalar las dependencias con `\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt`.

### 2. Configurar variables de entorno

Edita `.env`. Define una clave secreta aleatoria y configura las conexiones que correspondan. Ejemplo:

```dotenv
SECRET_KEY=reemplaza-por-una-clave-aleatoria-privada
SESSION_COOKIE_SECURE=0
OPERATIONAL_DATABASE_URL=sqlite:///data/presupuestos.db
CATALOG_DATABASE_URL=mysql+pymysql://usuario:clave@localhost/BIMetricsBD?charset=utf8mb4
MONGO_URI=mongodb+srv://usuario:clave@cluster.example.mongodb.net/
MONGO_DB_NAME=bimetrics_users
MONGO_ACTIVITY_DB_NAME=bimetrics_nosql
CORS_ORIGIN=http://localhost:5173,http://127.0.0.1:5173
```

`SESSION_COOKIE_SECURE=0` es para desarrollo local por HTTP. En producción configura HTTPS y establece `BIMETRICS_ENV=production` y `SESSION_COOKIE_SECURE=1`; la API se negará a iniciar si producción no tiene cookie segura o `SECRET_KEY` de al menos 32 caracteres. Si la contraseña de MongoDB contiene caracteres reservados de URI, codifícala correctamente. No compartas ni subas `.env`.

Variables principales:

| Variable | Uso |
|---|---|
| `SECRET_KEY` | Firma de la sesión Flask; obligatoria. |
| `OPERATIONAL_DATABASE_URL` | Base SQL para proyectos, presupuestos e insumos. SQLite local por defecto. |
| `CATALOG_DATABASE_URL` | Base SQL de catálogo; MySQL por defecto. |
| `MONGO_URI` | URI de MongoDB. |
| `MONGO_DB_NAME` | Base documental de usuarios y perfiles. |
| `MONGO_ACTIVITY_DB_NAME` | Base documental de actividad BIM. |
| `MONGO_DNS_SERVERS` | Resolutores DNS opcionales separados por comas para conexiones `mongodb+srv`. |
| `CORS_ORIGIN` | Orígenes permitidos para el frontend. |
| `SESSION_COOKIE_SECURE` | Requiere cookie segura en HTTPS cuando vale `1`. |

Para MySQL también puedes configurar `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD` y `MYSQL_DATABASE` en lugar de `CATALOG_DATABASE_URL`.

## Ejecución

### Opción A: iniciar frontend y backend juntos

Desde la raíz, con `.venv` activado en PowerShell:

```powershell
npm run dev
```

El comando inicia Flask y Vite en la misma terminal. Abre el frontend en `http://localhost:5173`; la API estará en `http://127.0.0.1:5000`. Para detener ambos procesos, pulsa `Ctrl+C`. También puedes iniciar el mismo lanzador con `python start.py`.

### Opción B: iniciar cada servicio por separado

Terminal 1, backend:

```powershell
\.venv\Scripts\Activate.ps1
Set-Location backend
python run.py
```

Terminal 2, frontend:

```powershell
Set-Location frontend-bimetrics
npm run dev
```

El backend requiere que MongoDB esté configurado. El catálogo maestro requiere MySQL, a menos que se utilice el modo local. Vite sirve la interfaz y se comunica con la API.

### Modo local con MongoDB en Docker

Si Atlas no es accesible desde tu red, el script `start_local.ps1` inicia o reutiliza un contenedor MongoDB local. Requiere Docker Desktop iniciado y el entorno `.venv` instalado:

```powershell
.\start_local.ps1
```

Este modo usa MongoDB en `127.0.0.1:27017` y un catálogo SQLite local en `data/catalogo-local.db`. No modifica la URI de Atlas guardada en `.env`. Los datos creados localmente no se sincronizan con Atlas ni con MySQL.

## Persistencia y datos

### Distribución

| Datos | Almacenamiento |
|---|---|
| Proyectos, presupuestos e insumos | SQL operacional |
| Partidas, variaciones y precios de referencia | MySQL (catálogo SQL) |
| Usuarios y preferencias | MongoDB (`bimetrics_users`) |
| Historial y metadatos de actividad BIM | MongoDB (`bimetrics_nosql`) |

MongoDB se utiliza para actividad BIM porque sus metadatos pueden cambiar según el evento, el software o el archivo. SQL se reserva para las entidades estructuradas y transaccionales.

### Catálogo de insumos

El catálogo fuente está en `data/catalogo/catalogo_precios_colombia.csv`; el volcado SQL correspondiente está en `data/catalogo/catalogo_precios_colombia.sql`. Las partidas y variaciones permanecen en SQL, no en MongoDB.

Validar el CSV sin conectarse a MySQL:

```powershell
Set-Location backend
..\.venv\Scripts\python.exe -m scripts.importar_catalogo_csv --dry-run
```

Importar el catálogo en la base configurada:

```powershell
..\.venv\Scripts\python.exe -m scripts.importar_catalogo_csv
```

Para regenerar el volcado SQL desde el CSV:

```powershell
..\.venv\Scripts\python.exe -m scripts.generar_catalogo_sql
```

Los precios del archivo son valores de referencia y no constituyen una cotización vigente. El CSV trae precios unitarios de las partidas, pero no desglosa cuadrillas ni rendimientos. Para acompañar las sugerencias de mano de obra, el catálogo SQL operacional incorpora jornales de referencia por perfil y ciudad con rango, fuente, fecha y metodología; no son ofertas vinculantes ni reemplazan una cotización del contratista. Los rangos se basan en referencias públicas de mercado 2026 y se agrupan por bandas de ciudad. Revisa si incluyen prestaciones, transporte, equipos, recargos e AIU antes de usar el valor contractual.

Cargar o actualizar las cotizaciones referenciales desde `backend/`:

```powershell
..\.venv\Scripts\python.exe -m scripts.cargar_cotizaciones_mano_obra
```

La carga es idempotente y escribe los perfiles sugeridos en `INSUMOS`, el precio aplicado por ciudad en `PRECIOS_CIUDAD` y el rango auditable en `COTIZACIONES_MANO_OBRA`. La interfaz muestra el rango, el valor usado, el método y el enlace a la fuente. Las sugerencias marcadas como condicionales aparecen desmarcadas para que el usuario confirme que el alcance requiere ese perfil. Las cantidades iniciales son un jornal por perfil y deben reemplazarse por cantidades y rendimientos del APU real. Entre las referencias consultadas están [tarifas de mano de obra por oficio y ciudad de Obra Maestra](https://obramaestra.com/co/guias/cuanto-cobrar-mano-de-obra-construccion-colombia) y [APU público de instalación metálica de Soluciones Excel](https://www.solucionesexcel.com/apu/2741-instalacion-nave-puerta-lamina/).

### Importación de cómputos TXT desde Revit y Archicad

En **Proyectos y presupuestos**, selecciona un presupuesto y pulsa **Importar TXT BIM**. Elige Revit o Archicad, carga un TXT tabulado exportado desde una planificación/tabla y revisa las coincidencias sugeridas por el catálogo SQL. La aplicación reconoce columnas de elemento o tipo y cantidad/conteo, admite UTF-8, UTF-16 y Windows-1252, y limita el archivo a 5 MB y 1000 filas. Cada fila se agrega manualmente tras revisar la partida sugerida. Los precios del TXT se ignoran: el servidor toma el precio de la partida/variación SQL. Los cambios de precios y el mantenimiento de insumos quedan restringidos a administradores.

### Datos de demostración y migraciones

Desde `backend/`, `python -m scripts.poblar_bd` carga datos de demostración. La opción `--reset` elimina las tablas operativas antes de cargarlas.

Hay scripts de migración para instalaciones anteriores. Revisa cuidadosamente sus variables de entorno y el origen/destino antes de ejecutarlos: una migración puede modificar datos persistentes.

## API principal

Las rutas de negocio requieren sesión, excepto las rutas de salud y registro/login. Todas las solicitudes que cambian datos deben enviar un encabezado `Origin` permitido por `CORS_ORIGIN`; las solicitudes sin ese encabezado se rechazan para reducir el riesgo de CSRF.

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/api/salud` | Estado de la API. |
| `GET` | `/api/salud/mongodb` | Comprueba MongoDB mediante `ping`. |
| `POST` | `/api/auth/registro` | Registra una cuenta. |
| `POST` | `/api/auth/login` | Inicia sesión. |
| `GET` | `/api/auth/sesion` | Consulta la sesión actual. |
| `POST` | `/api/auth/logout` | Cierra sesión. |
| `GET` | `/api/dashboard/resumen` | Combina métricas SQL con perfil y actividad MongoDB. |
| `POST` | `/api/presupuestos/{id}/partidas` | Agrega una partida del catálogo SQL con el precio asignado por el servidor. |
| `POST` | `/api/presupuestos/{id}/importar-txt/analizar` | Analiza un TXT tabulado de Revit o Archicad y devuelve sugerencias SQL sin modificar el presupuesto. |
| `POST` | `/api/actividades-bim` | Registra una actividad BIM en MongoDB. |
| `GET` | `/api/actividades-bim/<id>` | Consulta una actividad propia. |
| `PUT` | `/api/actividades-bim/<id>` | Actualiza campos permitidos de una actividad propia. |
| `DELETE` | `/api/actividades-bim/<id>` | Elimina una actividad propia. |
| `GET` | `/api/actividades-bim/usuario/<id>?limite=10` | Consulta el perfil y actividad reciente del usuario autorizado. |
| `GET` | `/api/partidas` | Consulta el catálogo SQL de partidas. |
| `POST` | `/api/partidas` | Crea una partida del catálogo maestro; solo para administradores. |
| `PUT`, `DELETE` | `/api/partidas/<codigo>` | Actualiza o elimina una partida; solo para administradores. |
| `GET` | `/api/presupuestos/<id>/pdf` | Descarga una exportación PDF del presupuesto, sin firma digital certificada. |
| `GET` | `/api/presupuestos/<id>/word` | Descarga DOCX editable, sin firma digital certificada. |
| `PUT` | `/api/presupuestos/<id>/aiu` | Actualiza administración, imprevistos y utilidad sobre costo directo; valores de 0 a 100. |
| — | `/api/proyectos`, `/api/presupuestos`, `/api/insumos` | Gestión de entidades operativas SQL. |

El CRUD documental valida los campos y comprueba la propiedad del documento. El endpoint mixto principal es `/api/dashboard/resumen`.

Los porcentajes AIU se definen para cada presupuesto y se aplican al costo directo. No se fijan tasas por defecto ni se presentan como tarifas legales: deben corresponder a las condiciones de cada obra y contrato. Los formatos PDF y Word incluyen el desglose; ninguno queda firmado digitalmente.

## Pruebas y calidad

El contrato OpenAPI en `docs/api/openapi.yaml` se valida en CI con `openapi-spec-validator`. El flujo ejecuta además `pip-audit` y `npm audit`; consulta el resultado del workflow de GitHub Actions para el estado vigente de dependencias. La comprobación a Atlas es externa a CI y debe ejecutarse desde el entorno de despliegue con su URI secreta configurada.

Ejecutar las pruebas del backend desde `backend/`:

```powershell
..\.venv\Scripts\python.exe -m pytest -q
```

Ejecutar lint y compilación del frontend desde `frontend-bimetrics/`:

```powershell
npm run lint
npm run build
```

Verificación del cierre: **31 pruebas aprobadas**. Las pruebas usan SQLite en memoria y MongoDB simulado; no son una prueba de conexión real a Atlas.

Para documentar una ejecución contra Atlas, registra capturas reales de:

1. `GET /api/salud/mongodb` con respuesta exitosa.
2. Un documento de actividad en Atlas Data Explorer.
3. `GET /api/dashboard/resumen` mostrando datos de ambas persistencias.

Oculta URI, contraseñas, tokens y datos personales en las capturas.

## Solución de problemas

### `SECRET_KEY` faltante

Comprueba que `.env` exista en la raíz y que contenga una `SECRET_KEY` no vacía.

### MongoDB aparece desconectado

1. Comprueba que la URI de `MONGO_URI` corresponda al clúster y al usuario de **Database Access**.
2. Confirma que la IP de salida de tu red esté permitida en Atlas **Network Access**.
3. Comprueba `GET /api/salud/mongodb` y revisa la terminal del backend.
4. Si Atlas no es accesible desde esa red, usa el modo local con Docker.

Que Flask inicie no garantiza que MongoDB esté conectado; la ruta de salud ejecuta la comprobación efectiva.

### MySQL no está disponible

Revisa el servicio MySQL, host, puerto, usuario, contraseña y nombre de la base en `CATALOG_DATABASE_URL` o en las variables `MYSQL_*`. Para desarrollo local puedes iniciar el catálogo SQLite mediante `start_local.ps1`.

## Entrega 3

Consulta el [cierre de seguridad, casos de uso y evidencias](docs/entrega-3/README.md).

## Documentación

- [Contrato OpenAPI](docs/api/openapi.yaml)
- [API y control de acceso](docs/arquitectura/api-y-control-acceso.md)
- [Arquitectura de persistencia políglota](docs/arquitectura/persistencia-poliglota.md)
- [Diagrama del esquema SQL](docs/diagramas/esquema_presupuestos_lucidchart.csv)
- [Justificación de persistencia NoSQL (PDF)](docs/entregables/justificacion_persistencia_poliglota.pdf)

## Seguridad

- No subas `.env`, URI de MongoDB ni credenciales al repositorio.
- Usa una clave `SECRET_KEY` privada y aleatoria.
- En producción, define `BIMETRICS_ENV=production`, sirve mediante HTTPS y activa `SESSION_COOKIE_SECURE=1`.
- Restringe el acceso de red de Atlas a las IP necesarias.
