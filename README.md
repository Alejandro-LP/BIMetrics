# BIMetrics

Aplicación web para administrar proyectos, presupuestos de obra y actividad BIM. El repositorio contiene una API Flask, una interfaz React y una arquitectura de persistencia políglota.

## Stack

- **Frontend:** React, Vite, Tailwind CSS y Framer Motion.
- **API:** Python, Flask y SQLAlchemy.
- **SQL operacional:** SQLite por defecto para proyectos, presupuestos e insumos.
- **SQL de catálogo:** MySQL para partidas y opciones parametrizadas.
- **NoSQL:** MongoDB para usuarios, preferencias e historial de actividad BIM.

## Estructura

```text
backend/
  app/
    routes/       Endpoints HTTP
    services/     Casos de uso y acceso a datos
    models.py     Esquema SQL operacional
    catalog_models.py
  scripts/        Importación, exportación y migración de datos
  tests/          Pruebas de API y servicios
frontend-bimetrics/
  src/
    app/ components/ features/ services/ styles/
data/
  catalogo/       CSV fuente y volcado SQL de precios de Colombia
docs/
  arquitectura/   Decisiones y persistencia
  diagramas/      Diagramas del modelo
  legal/          Términos y política de datos
```

## Requisitos

- Python 3.14.2 (versión fijada en `.python-version`)
- Node.js 24.13.0 LTS y npm (versión fijada en `.nvmrc`)
- MongoDB accesible para autenticación, perfiles y actividad BIM
- MySQL accesible para el catálogo de partidas

El SQL operacional usa SQLite local por defecto. MongoDB y MySQL pueden ejecutarse localmente o en servicios administrados.

Las versiones de dependencias del frontend están registradas en `frontend-bimetrics/package-lock.json`; las del backend se instalan desde `backend/requirements.txt`.

## Configuración local

Desde la raíz del repositorio, crea el entorno e instala dependencias:

```powershell
uv venv --python 3.14.2 .venv
uv pip install --python .venv\Scripts\python.exe -r backend\requirements.txt
\.venv\Scripts\Activate.ps1
Copy-Item .env.example .env
cd frontend-bimetrics
npm install
cd ..
```

Configura `.env` con una `SECRET_KEY` aleatoria y los datos de conexión. Variables principales:

| Variable | Uso |
|---|---|
| `SECRET_KEY` | Firma la sesión de Flask. Obligatoria. |
| `CATALOG_DATABASE_URL` | MySQL del catálogo maestro. |
| `OPERATIONAL_DATABASE_URL` | SQL de proyectos y presupuestos; SQLite local por defecto. |
| `MONGO_URI` | Dirección del servidor MongoDB. |
| `MONGO_DNS_SERVERS` | Resolutores alternos opcionales, separados por comas, para URI Atlas `mongodb+srv`. |
| `MONGO_DB_NAME` | Base de usuarios y perfiles (`bimetrics_users`). |
| `MONGO_ACTIVITY_DB_NAME` | Base de actividades BIM (`bimetrics_nosql`). |
| `CORS_ORIGIN` | Orígenes web permitidos. |
| `SESSION_COOKIE_SECURE` | Usa `0` en desarrollo HTTP; en producción, HTTPS y `1`. |

El catálogo usa MySQL por defecto. Ajusta `CATALOG_DATABASE_URL` o las variables `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD` y `MYSQL_DATABASE` según tu entorno. No subas `.env` ni secretos al repositorio.

## Ejecución

Con MongoDB y MySQL disponibles, inicia la API y Vite desde la raíz:

```powershell
python start.py
```

El lanzador requiere el entorno `.venv` y `npm` en `PATH`. También puedes iniciar cada servicio por separado:

```powershell
# Terminal 1
.\.venv\Scripts\Activate.ps1
cd backend
python run.py

# Terminal 2
cd frontend-bimetrics
npm run dev
```

La API queda en `http://127.0.0.1:5000`; Vite muestra la dirección local al iniciar. `GET /api/salud` comprueba Flask y `GET /api/salud/mongodb` verifica el acceso documental.

### Desarrollo temporal con MongoDB local

Si Atlas no está accesible desde la red actual, puedes iniciar BIMetrics con MongoDB local sin modificar la URI de Atlas guardada en `.env`. Requiere Docker Desktop iniciado y el entorno `.venv` preparado:

```powershell
.\start_local.ps1
```

El script inicia (o reutiliza) el contenedor oficial `mongo:8.0`, limitado a `127.0.0.1:27017`, y usa el volumen persistente `bimetrics-mongodb-data`. Durante esa ejecución solo, el backend usa `mongodb://127.0.0.1:27017`; la URI de Atlas en `.env` no se cambia. El catálogo SQL usa `data/catalogo-local.db` para esta sesión. Los registros y actividades creados en este modo quedan en las bases locales y no se sincronizan con Atlas ni con MySQL. Detén los servidores con `Ctrl+C`; Docker conservará los datos para la próxima ejecución.

## Catálogo de insumos y sugerencias de mano de obra

El catálogo de precios incluido en `data/catalogo/catalogo_precios_colombia.csv` contiene partidas con código, descripción, unidad, precio de referencia y opciones de variación exportadas del Excel. Esta es la fuente de precios del proyecto; no se usa el antiguo ejemplo SQL con precios ilustrativos. El volcado SQL con el mismo catálogo está en `data/catalogo/catalogo_precios_colombia.sql`; para regenerarlo desde el CSV, ejecuta desde `backend/`:

```powershell
python -m scripts.generar_catalogo_sql
```

El archivo SQL crea las tablas `partidas` y `variaciones_opciones` si no existen, y carga los precios y variaciones. Selecciona la base de datos BIMetrics antes de importarlo. Para la carga directa desde la aplicación, usa el importador CSV:

**Las partidas y sus variaciones quedan almacenadas en SQL (MySQL); no se guardan en MongoDB.** Al agregarlas a un presupuesto, la app crea o reutiliza el insumo correspondiente en la base SQL operativa (SQLite local por defecto, configurable a otro motor SQL).

El importador valida el CSV sin cargar Flask ni conectarse a MongoDB. Para la escritura en MySQL, el Python usado para ejecutarlo necesita `SQLAlchemy` y `PyMySQL` instalados.

```powershell
cd backend
python -m scripts.importar_catalogo_csv --dry-run
python -m scripts.importar_catalogo_csv
```

El panel **Catálogo maestro de insumos** reemplaza la lista de insumos de demostración y consulta los códigos, descripciones, unidades y precios del catálogo SQL de partidas desde `/api/partidas`. Permite buscar y cargar todos los insumos del catálogo, y agregar uno al presupuesto. El detalle muestra las opciones y precios variables importados. Al seleccionar un insumo u opción, BIMetrics lo crea o reutiliza en el catálogo operativo con código, unidad y precio, asociándolo a la ciudad del proyecto. Revisa la cotización antes de calcular: el precio del archivo es una referencia y no una oferta vigente.

La app sugiere perfiles habituales mediante reglas de palabras clave en la descripción (por ejemplo, mampostería, estructura, electricidad, instalaciones hidrosanitarias y acabados). Indica qué perfiles ya aparecen en los insumos de la ciudad y cuáles faltan. Al añadir un insumo, marca automáticamente los recursos de mano de obra sugeridos que ya tengan una tarifa positiva para la ciudad y los guarda junto con el insumo en una sola transacción SQL. La cantidad inicial de cada recurso es 1 unidad y puede ajustarse o desmarcarse antes de guardar. Si todavía no existe una tarifa local para un perfil, la app lo informa y no inventa un precio. Son orientaciones para revisión humana: no calculan rendimientos, composición de cuadrillas, cargas prestacionales ni tarifas por oficio.

Como contexto legal consultado para Colombia en 2026, el Decreto 0159 fija transitoriamente el salario mínimo mensual en **$1.750.905 COP** ([texto oficial](https://dapre.presidencia.gov.co/normativa/normativa/DECRETO%20No.%200159%20DEL%2019%20DE%20FEBRERO%20DE%202026.pdf)); el Decreto 1470 fija el auxilio de transporte en **$249.095 COP** para personas trabajadoras que cumplen sus condiciones ([texto oficial](https://www.presidencia.gov.co/Documents/251230-Decreto-1470-MinTrabajo.pdf)). Estos valores no son tarifas de mercado ni costo total de contratación. Para actualizar costos de construcción por periodo, consulta el [ICOCED del DANE](https://www.dane.gov.co/index.php/estadisticas-por-tema/precios-y-costos/indice-de-costos-de-la-construccion-de-edificaciones-icoced); el índice sirve para observar variaciones de costos y no reemplaza una cotización de mano de obra por oficio.

## Persistencia y API

Los proyectos, presupuestos e insumos se consultan en SQL. MongoDB almacena las identidades y los documentos flexibles de actividad BIM, incluidos metadatos variables de importaciones. La guía de arquitectura describe las colecciones, índices y operaciones disponibles: [persistencia políglota](docs/arquitectura/persistencia-poliglota.md). La justificación académica para la entrega está en [el PDF de persistencia políglota](docs/entregables/justificacion_persistencia_poliglota.pdf).

Rutas principales:

- `POST /api/auth/registro`, `POST /api/auth/login`, `GET /api/auth/sesion`, `POST /api/auth/logout`
- `GET /api/dashboard/resumen` (combina métricas SQL con perfil y actividad BIM de MongoDB)
- `/api/proyectos`, `/api/presupuestos`, `/api/insumos`
- `/api/actividades-bim` (CRUD documental; requiere MongoDB)
- `/api/partidas` (catálogo MySQL)

Las rutas de negocio requieren sesión. Las contraseñas se guardan como hashes.

## Datos y migraciones

Valida el CSV del catálogo sin conectarte a MySQL:

```powershell
cd backend
python -m scripts.importar_catalogo_csv --dry-run
```

Para importar el catálogo, elimina `--dry-run` con MySQL configurado. Los scripts `migrar_operativo_sqlite.py` y `migrar_usuarios_mongodb.py` permiten migrar datos de instalaciones anteriores; revisa sus variables de entorno antes de ejecutarlos.

`python -m scripts.poblar_bd` carga datos locales de demostración. La opción `--reset` borra las tablas operativas antes de sembrar los datos.

## Evidencias de ejecución

Suite ejecutada localmente el 2 de noviembre de 2026 con Python 3.14.2:

```text
..\.venv\Scripts\python.exe -m pytest -q
........................                                                 [100%]
24 passed in 2.81s
```

Las pruebas documentales usan `mongomock` y SQLite en memoria para comprobar CRUD, autorización y el endpoint combinado sin acceder a Atlas. Esta salida no afirma una conexión en vivo a Atlas. Para la evidencia de despliegue, conserva además una captura real de `GET /api/salud/mongodb`, del documento de actividad en Atlas Data Explorer y de `GET /api/dashboard/resumen`, ocultando credenciales y datos personales.

## Desarrollo

Desde `backend/`, ejecuta las pruebas:

```powershell
python -m pytest -q
```

Desde `frontend-bimetrics/`, ejecuta análisis estático y compilación:

```powershell
npm run lint
npm run build
```
