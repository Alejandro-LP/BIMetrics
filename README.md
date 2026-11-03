# BIMetrics

Aplicación web para gestionar proyectos y presupuestos de obra, consultar un catálogo de insumos y registrar actividad BIM. El sistema combina persistencia relacional (SQL) con almacenamiento documental (MongoDB).

## Contenido

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

## Características

- Administración de proyectos, presupuestos e insumos.
- Catálogo SQL de partidas, variaciones y precios de referencia.
- Sugerencias de mano de obra a partir de la descripción de los insumos y las tarifas disponibles para la ciudad.
- Registro de usuarios, preferencias y actividad BIM.
- Dashboard que reúne información SQL y MongoDB.
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

`SESSION_COOKIE_SECURE=0` es para desarrollo local por HTTP. En producción configura HTTPS y establece el valor en `1`. Si la contraseña de MongoDB contiene caracteres reservados de URI, codifícala correctamente. No compartas ni subas `.env`.

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

Desde la raíz:

```powershell
\.venv\Scripts\python.exe start.py
```

Abre el frontend en `http://localhost:5173`. La API estará en `http://127.0.0.1:5000`. Para detener ambos procesos, pulsa `Ctrl+C` en la terminal.

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
\.\start_local.ps1
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

Los precios del archivo son valores de referencia y no constituyen una cotización vigente. Las sugerencias de mano de obra son orientativas; la aplicación no calcula rendimientos ni costos completos de contratación.

### Datos de demostración y migraciones

Desde `backend/`, `python -m scripts.poblar_bd` carga datos de demostración. La opción `--reset` elimina las tablas operativas antes de cargarlas.

Hay scripts de migración para instalaciones anteriores. Revisa cuidadosamente sus variables de entorno y el origen/destino antes de ejecutarlos: una migración puede modificar datos persistentes.

## API principal

Las rutas de negocio requieren sesión, excepto las rutas de salud y registro/login.

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/api/salud` | Estado de la API. |
| `GET` | `/api/salud/mongodb` | Comprueba MongoDB mediante `ping`. |
| `POST` | `/api/auth/registro` | Registra una cuenta. |
| `POST` | `/api/auth/login` | Inicia sesión. |
| `GET` | `/api/auth/sesion` | Consulta la sesión actual. |
| `POST` | `/api/auth/logout` | Cierra sesión. |
| `GET` | `/api/dashboard/resumen` | Combina métricas SQL con perfil y actividad MongoDB. |
| `POST` | `/api/actividades-bim` | Registra una actividad BIM en MongoDB. |
| `GET` | `/api/actividades-bim/<id>` | Consulta una actividad propia. |
| `PUT` | `/api/actividades-bim/<id>` | Actualiza campos permitidos de una actividad propia. |
| `DELETE` | `/api/actividades-bim/<id>` | Elimina una actividad propia. |
| `GET` | `/api/actividades-bim/usuario/<id>?limite=10` | Consulta el perfil y actividad reciente del usuario autorizado. |
| `GET` | `/api/partidas` | Consulta el catálogo SQL de partidas. |
| — | `/api/proyectos`, `/api/presupuestos`, `/api/insumos` | Gestión de entidades operativas SQL. |

El CRUD documental valida los campos y comprueba la propiedad del documento. El endpoint mixto principal es `/api/dashboard/resumen`.

## Pruebas y calidad

Ejecutar las pruebas del backend desde `backend/`:

```powershell
..\.venv\Scripts\python.exe -m pytest -q
```

Ejecutar lint y compilación del frontend desde `frontend-bimetrics/`:

```powershell
npm run lint
npm run build
```

Última ejecución registrada: **24 pruebas aprobadas**. Las pruebas usan SQLite en memoria y MongoDB simulado; no son una prueba de conexión real a Atlas.

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

## Documentación

- [Arquitectura de persistencia políglota](docs/arquitectura/persistencia-poliglota.md)
- [Diagrama del esquema SQL](docs/diagramas/esquema_presupuestos_lucidchart.csv)
- [Justificación de persistencia NoSQL (PDF)](docs/entregables/justificacion_persistencia_poliglota.pdf)

## Seguridad

- No subas `.env`, URI de MongoDB ni credenciales al repositorio.
- Usa una clave `SECRET_KEY` privada y aleatoria.
- En producción, sirve la aplicación mediante HTTPS y activa `SESSION_COOKIE_SECURE=1`.
- Restringe el acceso de red de Atlas a las IP necesarias.
