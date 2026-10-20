# BIMetrics

Aplicación web para gestionar proyectos y presupuestos de obra. El frontend está hecho con React y Vite; la API usa Python, Flask y SQLAlchemy. SQLite es la base de datos predeterminada. MongoDB se usa para el historial de actividad BIM.

## Requisitos

- Python 3.9 o superior
- Node.js y npm
- MongoDB solo para usar las funciones de actividad BIM

## Instalación en Windows (PowerShell)

Ejecuta estos comandos desde la carpeta raíz del proyecto:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
Copy-Item .env.example .env
```

Abre `.env` y configura `SECRET_KEY` con un valor aleatorio privado. Puedes generarlo con:

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

Para desarrollo local por HTTP, usa `SESSION_COOKIE_SECURE=0`. En producción, publica la aplicación detrás de HTTPS y configura `SESSION_COOKIE_SECURE=1`. No uses la clave de ejemplo en producción.

Instala las dependencias del frontend:

```powershell
cd frontend-bimetrics
npm install
```

## Iniciar la aplicación

Deja el frontend y la API corriendo en terminales separadas.

**Terminal 1: API Flask**, desde la raíz del proyecto:

```powershell
.\.venv\Scripts\Activate.ps1
cd backend
python run.py
```

La API queda disponible en `http://127.0.0.1:5000`. La base SQLite y sus tablas se crean automáticamente al iniciar.

**Terminal 2: frontend**, desde la raíz del proyecto:

```powershell
cd frontend-bimetrics
npm run dev
```

Abre la dirección que indique Vite, normalmente `http://localhost:5173`. El proxy de desarrollo envía las solicitudes `/api` a Flask en `http://localhost:5000`.

Comprueba que la API está activa visitando `http://127.0.0.1:5000/api/salud`; debe responder `{"estado":"ok"}`.

## Datos de demostración

El sistema permite crear una cuenta desde `/registro`. Para cargar el proyecto y presupuesto de demostración, detén la API y ejecuta desde `backend/`:

```powershell
python -m scripts.poblar_bd
```

Si ya hay proyectos, el script no los reemplaza. La opción `--reset` borra los datos existentes antes de cargar la demo; úsala solo si quieres restablecer la base:

```powershell
python -m scripts.poblar_bd --reset
```

La cuenta de demostración no tiene credenciales de acceso; crea una cuenta desde la aplicación para iniciar sesión.

## Configuración

La configuración se lee desde `.env` en la raíz:

| Variable | Uso | Valor predeterminado |
|---|---|---|
| `SECRET_KEY` | Firma las cookies de sesión. Obligatoria para iniciar Flask. | Sin valor |
| `SESSION_COOKIE_SECURE` | Exige HTTPS para enviar la cookie. | `0` |
| `DATABASE_URL` | Conexión SQL. | SQLite en `data/presupuestos.db` |
| `CORS_ORIGIN` | Orígenes web permitidos, separados por comas. | `http://localhost:5173,http://127.0.0.1:5173` |
| `MONGO_URI` | Conexión MongoDB para actividades BIM. | `mongodb://localhost:27017` |
| `MONGO_DB_NAME` | Base de datos MongoDB. | `bimetrics_nosql` |
| `FLASK_DEBUG` | Activa el modo de depuración local. | `0` |

Para usar MySQL, instala el controlador `pymysql` (`pip install pymysql`) y configura, por ejemplo, `DATABASE_URL=mysql+pymysql://usuario:clave@localhost:3306/bimetrics_db`.

MongoDB no es necesario para iniciar la API ni usar los flujos principales de proyectos y presupuestos. Las rutas de actividad BIM requieren que MongoDB esté disponible.

## Estructura

```text
backend/
  app/
    routes/       Endpoints Flask (auth, proyectos, insumos, presupuestos, BIM)
    services/     Lógica de negocio y exportación Excel
    models.py     Esquema SQLAlchemy Core
  scripts/        Carga de datos de demostración
  tests/          Pruebas de API, servicios y actividad BIM
  run.py          Inicio de la API
frontend-bimetrics/
  src/
    app/          Rutas y composición de React
    components/   Componentes compartidos y layouts
    features/     Autenticación, dashboard, perfil y páginas públicas
    services/     Cliente HTTP para la API
    styles/       Estilos globales
docs/             Documentación técnica y diagramas
data/             Base SQLite local (no se incluye en Git)
```

## Pruebas y compilación

Desde la raíz, con el entorno virtual activo:

```powershell
cd backend
python -m pytest -q
cd ..\frontend-bimetrics
npm run lint
npm run build
```

## API

La API usa el prefijo `/api`. Las rutas de negocio requieren iniciar sesión; el registro, login, consulta de sesión, cierre de sesión y estado de salud son públicos.

- `GET /api/salud`
- `POST /api/auth/registro`, `POST /api/auth/login`, `GET /api/auth/sesion`, `POST /api/auth/logout`
- `PUT /api/auth/perfil`
- `/api/dashboard/resumen`
- `/api/insumos`, `/api/usuarios`, `/api/proyectos`, `/api/presupuestos`
- `/api/actividades-bim` (requiere MongoDB)

Las contraseñas se almacenan como hashes. El registro permite los roles `arquitecto`, `ingeniero` y `cliente`; el rol administrador no puede elegirse desde el formulario público.
