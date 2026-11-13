# BIMetrics

Aplicación web integral para la gestión de proyectos y presupuestos de obra en Colombia, consulta de catálogo de partidas con variaciones, estimación de mano de obra y registro de trazabilidad de actividad BIM.

El sistema implementa una **arquitectura de persistencia políglota**, combinando persistencia relacional SQL (SQLite para datos operacionales y MySQL para el catálogo maestro) con almacenamiento documental NoSQL en MongoDB (usuarios, preferencias y actividad BIM).

---

## Contenido

- [Características principales](#características-principales)
- [Arquitectura del sistema](#arquitectura-del-sistema)
- [Requisitos previos](#requisitos-previos)
- [Instalación y configuración](#instalación-y-configuración)
  - [1. Clonar el repositorio y preparar entornos](#1-clonar-el-repositorio-y-preparar-entornos)
  - [2. Configurar variables de entorno](#2-configurar-variables-de-entorno)
  - [3. Preparar el primer administrador](#3-preparar-el-primer-administrador)
- [Ejecución](#ejecución)
  - [Opción A: Lanzador conjunto (Recomendado)](#opción-a-lanzador-conjunto-recomendado)
  - [Opción B: Modo local con Docker Desktop](#opción-b-modo-local-con-docker-desktop)
  - [Opción C: Iniciar servicios por separado](#opción-c-iniciar-servicios-por-separado)
- [Guion de demostración y pruebas](#guion-de-demostración-y-pruebas)
  - [Casos de prueba funcionales](#casos-de-prueba-funcionales)
  - [Prueba de endpoints protegidos por API](#prueba-de-endpoints-protegidos-por-api)
- [Persistencia, datos y scripts](#persistencia-datos-y-scripts)
  - [Distribución de datos](#distribución-de-datos)
  - [Gestión y mantenimiento del catálogo](#gestión-y-mantenimiento-del-catálogo)
  - [Importación de cómputos TXT (Revit y Archicad)](#importación-de-cómputos-txt-revit-y-archicad)
  - [Scripts utilitarios disponibles](#scripts-utilitarios-disponibles)
- [Referencia de la API REST](#referencia-de-la-api-rest)
- [Pruebas y calidad de código](#pruebas-y-calidad-de-código)
- [Solución de problemas comunes](#solución-de-problemas-comunes)
- [Documentación técnica](#documentación-técnica)
- [Seguridad](#seguridad)

---

## Características principales

- **Gestión integral de presupuestos:** Creación y estructuración de proyectos de obra, capítulos, partidas e insumos con cálculo automatizado de costos directos y aplicación de porcentajes de AIU (Administración, Imprevistos y Utilidad).
- **Catálogo de partidas y variaciones:** Búsqueda en catálogo SQL con tolerancia a errores tipográficos y sugerencias fonéticas/aproximadas.
- **Sugerencias de mano de obra y jornales de referencia:** Recomendación de cuadrillas (oficial, ayudante, técnico) basadas en rendimientos APU y cotizaciones referenciales por ciudad (Bogotá, Medellín, Cali, Barranquilla, Bucaramanga, etc.).
- **Importación de cómputos BIM:** Procesamiento de tablas tabuladas en texto plano (`.txt`) exportadas desde Autodesk Revit y Graphisoft Archicad, asociando elementos a partidas SQL con validación de codificación (UTF-8, UTF-16, Windows-1252).
- **Exportación multiformato:** Generación y descarga de presupuestos en hojas de cálculo Excel (`.xlsx`), documentos editables Word (`.docx`) e informes en formato PDF.
- **Control de acceso basado en roles (RBAC):**
  - `administrador`: Control total del catálogo maestro, mantenimiento de insumos y administración de usuarios.
  - `arquitectura` e `ingenieria`: Creación y edición de proyectos propios, presupuestos, análisis y colaboración mediante códigos de invitación.
  - `cliente`: Perfil con permisos de solo lectura para supervisión y consulta de presupuestos aprobados.
- **Recuperación segura de contraseñas:** Flujo de restablecimiento mediante tokens de un solo uso con caducidad temporal (30 minutos), soporte de entrega por correo SMTP y modo de depuración en pantalla para desarrollo local.
- **Trazabilidad y registro de actividad BIM:** Registro documental en MongoDB de eventos de modelado, exportaciones y modificaciones por usuario y proyecto.
- **Dashboard políglota unificado:** Endpoint que sintetiza en tiempo real métricas transaccionales SQL con metadatos de usuario y actividad documental NoSQL.

---

## Arquitectura del sistema

BIMetrics desacopla sus componentes para maximizar la integridad transaccional y la flexibilidad en datos no estructurados:

| Componente | Tecnología | Responsabilidad |
|---|---|---|
| **Frontend** | React 19, Vite, Tailwind CSS, Lucide React, Framer Motion | Interfaz de usuario SPA responsiva, gestión de vistas y consumo de API. |
| **Backend** | Python 3.14, Flask 3.1, SQLAlchemy 2, PyMongo | API RESTful, control de sesiones, validaciones de seguridad y lógica de negocio. |
| **SQL Operacional** | SQLite (por defecto: `data/presupuestos.db`) | Entidades estructuradas transaccionales: proyectos, colaboradores, presupuestos, detalles e insumos. |
| **SQL Catálogo** | MySQL (o SQLite local para pruebas: `data/catalogo-local.db`) | Catálogo maestro de partidas, unidades, precios de referencia y variaciones. |
| **NoSQL Documental** | MongoDB (`bimetrics_users` y `bimetrics_nosql`) | Colecciones de identidades de usuario, credenciales hasheadas, preferencias y actividad BIM variable. |

```mermaid
flowchart LR
    UI["Frontend (React + Vite)<br/>:5173"] -->|"Llamadas API REST<br/>Cookies SameSite=Lax"| API["Backend (Flask REST API)<br/>:5000"]
    API -->|"SQLAlchemy<br/>(Transaccional)"| SQL[("SQL Operacional<br/>SQLite")]
    API -->|"Flask-SQLAlchemy<br/>(Catálogo)"| CAT[("SQL Catálogo Maestro<br/>MySQL / SQLite")]
    API -->|"PyMongo<br/>(Identidad y Eventos)"| MONGO[("MongoDB<br/>Atlas / Local")]
```

> [!NOTE]
> Las relaciones entre motores se articulan mediante identificadores lógicos (`id_usuario`, `id_proyecto`). No existen transacciones distribuidas complejas ni acoplamiento rígido entre SQL y NoSQL.

---

## Requisitos previos

- **Python:** 3.14.2 (o versión `>=3.11` compatible indicada en `.python-version`).
- **Node.js:** v24.13.0 (indicada en `.nvmrc`) y gestor de paquetes **npm**.
- **uv:** Herramienta recomendada para la gestión rápida de entornos virtuales de Python ([instalación de uv](https://docs.astral.sh/uv/)). De forma alternativa, se puede usar el módulo estándar `venv` y `pip`.
- **Motor de persistencia:**
  - Instancia de **MongoDB** accesible (clúster en MongoDB Atlas o servicio local vía Docker).
  - Instancia de **MySQL** para el catálogo maestro (opcional si se utiliza el modo de prueba local con Docker o SQLite).

---

## Instalación y configuración

### 1. Clonar el repositorio y preparar entornos

Ejecuta desde PowerShell (Windows) o Bash (Linux/macOS):

```powershell
# Clonar el repositorio
git clone https://github.com/Alejandro-LP/BIMetrics.git
Set-Location BIMetrics

# Crear y activar entorno virtual de Python
uv venv --python 3.14.2 .venv
# En Windows:
.\.venv\Scripts\Activate.ps1
# En Linux/macOS: source .venv/bin/activate

# Instalar dependencias del backend
uv pip install -r backend\requirements.txt

# Instalar dependencias del frontend
npm --prefix frontend-bimetrics install

# Crear archivo de configuración local a partir de la plantilla
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

*(Si no usas `uv`, crea el entorno con `python -m venv .venv` e instala con `.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt`).*

### 2. Configurar variables de entorno

Edita el archivo `.env` en la raíz del proyecto. Variables esenciales:

```dotenv
# Clave secreta para firma de cookies de sesión (generar con python -c "import secrets; print(secrets.token_hex(32))")
SECRET_KEY=clave_secreta_privada_y_aleatoria_de_al_menos_32_caracteres

# Cookies seguras: 0 para desarrollo local HTTP; 1 para producción con HTTPS
SESSION_COOKIE_SECURE=0
BIMETRICS_ENV=development

# Bases de datos SQL
OPERATIONAL_DATABASE_URL=sqlite:///data/presupuestos.db
CATALOG_DATABASE_URL=mysql+pymysql://usuario:password@localhost/BIMetricsBD?charset=utf8mb4

# Orígenes CORS permitidos (separados por comas)
CORS_ORIGIN=http://localhost:5173,http://127.0.0.1:5173

# MongoDB (Atlas o local)
MONGO_URI=mongodb+srv://usuario:password@cluster.mongodb.net/
MONGO_DB_NAME=bimetrics_users
MONGO_ACTIVITY_DB_NAME=bimetrics_nosql
# MONGO_DNS_SERVERS=1.1.1.1,8.8.8.8 # Opcional si la red local tiene problemas de resolución SRV

# Recuperación de contraseñas
APP_BASE_URL=http://localhost:5173
PASSWORD_RESET_DEBUG=1 # En desarrollo local muestra el enlace en la UI; usar 0 en producción
# SMTP_HOST=smtp.example.com
# SMTP_PORT=587
# SMTP_USERNAME=usuario-smtp
# SMTP_PASSWORD=clave-smtp
# SMTP_FROM=no-reply@example.com
# SMTP_USE_TLS=1
```

### 3. Preparar el primer administrador

Por directriz de seguridad, el formulario público de registro no permite autoasignarse el rol de administrador.

Para inicializar la primera cuenta administrativa:
1. Inicia el backend al menos una vez para validar la conexión con MongoDB.
2. Desde la carpeta `backend/`, ejecuta:
   ```powershell
   Set-Location backend
   ..\.venv\Scripts\python.exe -m scripts.crear_administrador
   Set-Location ..
   ```
3. El asistente interactivo solicitará nombre, correo y contraseña. Solo creará la cuenta si no existe un administrador en la base de datos.
4. Las cuentas administradoras subsiguientes podrán ser creadas por este administrador mediante la API en `POST /api/usuarios`.

---

## Ejecución

### Opción A: Lanzador conjunto (Recomendado)

Desde la raíz del repositorio, ejecuta:

```powershell
npm run dev
# o alternativamente:
.\.venv\Scripts\python.exe start.py
```

El script inicia en paralelo el servidor Flask (`http://127.0.0.1:5000`) y el servidor Vite (`http://localhost:5173`). Al pulsar `Ctrl+C`, ambos procesos se detienen de forma limpia.

### Opción B: Modo local con Docker Desktop

Si no tienes acceso a MongoDB Atlas o a una base MySQL remota, el script automatizado `start_local.ps1` levanta un contenedor local de MongoDB en Docker y utiliza una base SQLite local para el catálogo:

```powershell
.\start_local.ps1
```

- Inicia o reutiliza el contenedor Docker `bimetrics-mongodb-local` en el puerto `27017`.
- Configura temporalmente `MONGO_URI=mongodb://127.0.0.1:27017` y el catálogo en `data/catalogo-local.db`.
- Lanza frontend y backend de manera inmediata.

### Opción C: Iniciar servicios por separado

Si prefieres monitorear los logs de cada servicio en terminales independientes:

**Terminal 1 — Backend (Flask):**
```powershell
.\.venv\Scripts\Activate.ps1
Set-Location backend
python run.py
```

**Terminal 2 — Frontend (Vite):**
```powershell
Set-Location frontend-bimetrics
npm run dev
```

---

## Guion de demostración y pruebas

Para evaluar o demostrar la plataforma, se recomienda seguir el siguiente guion con cuentas de prueba:

1. **Cuentas requeridas:**
   - Una cuenta con rol **Arquitectura** o **Ingeniería** (creada desde el formulario de registro).
   - Una cuenta con rol **Cliente** (creada desde el formulario de registro).
   - Una cuenta **Administrador** (creada mediante `scripts.crear_administrador`).

### Casos de prueba funcionales

| Caso | Acción a realizar | Resultado esperado |
|---|---|---|
| **Seguridad y RBAC** | Intentar consultar proyectos sin sesión activa. Iniciar sesión como `cliente` e intentar crear o modificar una partida de catálogo. | Respuesta `HTTP 401 Unauthorized` sin sesión. Respuesta `HTTP 403 Forbidden` en escrituras del cliente. |
| **CU-01 · Catálogo de partidas** | Como administrador, acceder a `/api/partidas` o al panel de partidas, crear una partida nueva, buscarla, editar su precio de referencia y eliminar una partida de prueba. | Operaciones exitosas con códigos HTTP 201, 200 y 204. Solo accesible a administradores. |
| **CU-02 · Cálculo y AIU** | Crear un presupuesto, asociar una partida (ej. 20 m de tubería o mampostería), configurar AIU (10% administración, 3% imprevistos, 7% utilidad) y solicitar el cálculo. | Desglose exacto de costo directo, valor de AIU y valor total de la obra. |
| **CU-03 · Exportación de documentos** | En la vista de presupuesto, descargar las versiones en **Excel (.xlsx)**, **Word (.docx)** y **PDF**. | Los tres archivos se generan y descargan correctamente con el desglose del presupuesto y resumen de AIU. |
| **CU-04 · Historial y duplicación** | Duplicar un presupuesto existente dentro del proyecto y consultar la trazabilidad. | Se genera un duplicado independiente actualizando los precios unitarios vigentes según la base destino. |
| **Persistencia políglota** | Registrar un evento de actividad BIM vinculado a la obra y consultar `GET /api/dashboard/resumen`. | El dashboard devuelve una respuesta unificada que integra métricas transaccionales SQL y el historial documental NoSQL de MongoDB. |

### Prueba de endpoints protegidos por API

En PowerShell 7, puedes probar el flujo completo con cookies de sesión y encabezado de origen:

```powershell
$api = 'http://127.0.0.1:5000/api'
$headers = @{ Origin = 'http://localhost:5173' }

# 1. Comprobaciones de salud
Invoke-RestMethod "$api/salud"
Invoke-RestMethod "$api/salud/sql"
Invoke-RestMethod "$api/salud/mongodb"

# 2. Iniciar sesión y capturar cookie de sesión
$credenciales = @{ email = 'admin@example.com'; password = 'TuPasswordSeguro123' } | ConvertTo-Json
Invoke-RestMethod "$api/auth/login" -Method Post -Headers $headers -ContentType 'application/json' -Body $credenciales -SessionVariable sesion

# 3. Consultar rutas protegidas utilizando la sesión autenticada
Invoke-RestMethod "$api/auth/sesion" -WebSession $sesion
Invoke-RestMethod "$api/proyectos" -WebSession $sesion
Invoke-RestMethod "$api/dashboard/resumen" -WebSession $sesion
```

---

## Persistencia, datos y scripts

### Distribución de datos

```
BIMetrics
├── SQL Operacional (SQLite: data/presupuestos.db)
│   ├── PROYECTOS, PROYECTO_COLABORADORES
│   ├── PRESUPUESTOS, DETALLE_PRESUPUESTO
│   └── INSUMOS, PRECIOS_CIUDAD, COTIZACIONES_MANO_OBRA
│
├── SQL Catálogo Maestro (MySQL / SQLite local)
│   ├── partidas (código, descripción, unidad, precio base)
│   ├── variaciones_opciones (opciones, factores y precios)
│   └── recomendaciones_mano_obra (rendimientos por jornal)
│
└── MongoDB NoSQL (Atlas / Local)
    ├── bimetrics_users: usuarios (credenciales hash, roles, perfil)
    └── bimetrics_nosql: actividades_bim (eventos y metadatos variables)
```

### Gestión y mantenimiento del catálogo

El catálogo maestro incluye más de 3.000 partidas y variaciones del sector de la construcción en Colombia:

- **Volcado SQL principal:** `data/catalogo/catalogo_precios_colombia.sql` (para importar en esquemas MySQL como `BIMetricsBD`).
- **Respaldo CSV:** `data/catalogo/catalogo_precios_colombia.csv`.
- **Validar CSV sin escribir en base de datos:**
  ```powershell
  Set-Location backend
  ..\.venv\Scripts\python.exe -m scripts.importar_catalogo_csv --dry-run
  ```
- **Cargar catálogo desde CSV a la base configurada:**
  ```powershell
  ..\.venv\Scripts\python.exe -m scripts.importar_catalogo_csv
  ```
- **Regenerar el volcado SQL a partir del CSV:**
  ```powershell
  ..\.venv\Scripts\python.exe -m scripts.generar_catalogo_sql
  ```

### Importación de cómputos TXT (Revit y Archicad)

La aplicación permite subir cómputos tabulados exportados desde Revit o Archicad:
- Admite archivos de hasta 5 MB y hasta 1.000 registros.
- Detección automática de codificaciones de texto (`UTF-8`, `UTF-16`, `Windows-1252`).
- Asocia automáticamente columnas de elemento/tipo y cantidad, proponiendo la partida correspondiente del catálogo SQL para revisión previa del usuario.

### Scripts utilitarios disponibles

Ejecutar siempre desde la carpeta `backend/` con el entorno virtual:

| Script | Descripción |
|---|---|
| `scripts.crear_administrador` | Crea interactivamente la cuenta administradora inicial en MongoDB. |
| `scripts.cargar_cotizaciones_mano_obra` | Carga o actualiza jornales de referencia y rangos de mano de obra por ciudad. |
| `scripts.cargar_recomendaciones_mano_obra` | Registra rendimientos APU y perfiles requeridos para partidas específicas en MySQL. |
| `scripts.poblar_bd` | Carga proyectos, presupuestos e insumos de prueba (usar `--reset` para limpiar tablas operacionales). |
| `scripts.diagnostico_atlas_remoto` | Valida la conexión de red, resolución DNS y latencia hacia MongoDB Atlas. |

---

## Referencia de la API REST

Todas las peticiones que mutan estado (`POST`, `PUT`, `PATCH`, `DELETE`) exigen el encabezado `Origin` coincidente con `CORS_ORIGIN`.

### Salud y diagnóstico
- `GET /api/salud`: Estado general de la API Flask.
- `GET /api/salud/sql`: Verifica conexión a la base de catálogo y conteo de partidas/variaciones.
- `GET /api/salud/mongodb`: Ejecuta ping de conectividad contra MongoDB.

### Autenticación y usuarios
- `POST /api/auth/registro`: Registro de nuevos usuarios (roles permitidos: `arquitectura`, `ingenieria`, `cliente`).
- `POST /api/auth/login`: Autenticación y emisión de cookie HttpOnly.
- `GET /api/auth/sesion`: Información de la sesión activa y perfil del usuario.
- `POST /api/auth/logout`: Invalidación de la cookie de sesión actual.
- `PUT /api/auth/perfil`: Actualización de información personal.
- `GET /api/auth/preferencias` / `PUT /api/auth/preferencias`: Consulta y actualización de preferencias de usuario.
- `POST /api/auth/solicitar-restablecimiento`: Emisión de token temporal para recuperación de contraseña.
- `POST /api/auth/restablecer-password`: Consumo de token y actualización de contraseña.
- `GET /api/usuarios` *(Solo Admin)*: Listado de usuarios del sistema.
- `POST /api/usuarios` *(Solo Admin)*: Creación de usuarios con cualquier rol (incluyendo administradores).
- `GET /api/usuarios/{id}` / `PUT /api/usuarios/{id}` / `DELETE /api/usuarios/{id}` *(Solo Admin)*: Mantenimiento de cuentas.

### Proyectos y colaboración
- `GET /api/proyectos`: Listado de proyectos accesibles al usuario autenticado.
- `POST /api/proyectos`: Creación de una nueva obra (nombre, cliente, ciudad).
- `GET /api/proyectos/{id}/presupuestos`: Historial de presupuestos y versiones de la obra.
- `POST /api/proyectos/{id}/invitaciones`: Generación de código de invitación (validez 7 días) para colaboradores o clientes.
- `POST /api/proyectos/invitaciones/aceptar`: Canje de código de invitación asociando al usuario al proyecto.
- `DELETE /api/proyectos/{id}`: Eliminación de proyecto (restringido al propietario).

### Presupuestos y exportaciones
- `GET /api/presupuestos`: Listado de presupuestos.
- `POST /api/presupuestos`: Creación de un presupuesto para un proyecto.
- `GET /api/presupuestos/{id}`: Detalle de partidas, insumos y cálculos del presupuesto.
- `PUT /api/presupuestos/{id}/aiu`: Actualización de porcentajes de administración, imprevistos y utilidad (0 - 100%).
- `POST /api/presupuestos/{id}/partidas`: Adición de partidas desde el catálogo SQL con precio verificado en servidor.
- `POST /api/presupuestos/{id}/detalles`: Adición de renglones o insumos personalizados.
- `DELETE /api/presupuestos/{id}/detalles/{id_detalle}`: Eliminación de un renglón del presupuesto.
- `POST /api/presupuestos/{id}/calcular`: Recálculo y consolidación de totales.
- `POST /api/presupuestos/{id}/duplicar`: Duplicación de versión presupuestaria.
- `POST /api/presupuestos/{id}/importar-txt/analizar`: Análisis de tabla tabulada de Revit o Archicad con sugerencias de partidas.
- `POST /api/presupuestos/{id}/mano-obra-asociada`: Sugerencias de jornales y cuadrillas requeridas.
- `GET /api/presupuestos/{id}/excel`: Descarga de presupuesto en formato Excel (`.xlsx`).
- `GET /api/presupuestos/{id}/pdf`: Descarga de presupuesto en formato PDF estructurado.
- `GET /api/presupuestos/{id}/word`: Descarga de presupuesto editable en formato Word (`.docx`).

### Catálogo de partidas e insumos
- `GET /api/partidas`: Listado paginado de partidas del catálogo maestro.
- `GET /api/partidas/buscar?q={termino}`: Búsqueda aproximada de partidas.
- `GET /api/partidas/{codigo}`: Detalle técnico y opciones de variación.
- `POST /api/partidas` *(Solo Admin)*: Creación de partida maestra.
- `PUT /api/partidas/{codigo}` / `DELETE /api/partidas/{codigo}` *(Solo Admin)*: Modificación y baja de partidas.
- `GET /api/insumos` / `POST /api/insumos`: Consulta y creación de insumos operacionales.
- `POST /api/insumos/ajuste-masivo` *(Solo Admin)*: Ajuste porcentual de costos de insumos.

### Actividades BIM y Dashboard
- `POST /api/actividades-bim`: Registro de evento documental de modelado BIM en MongoDB.
- `GET /api/actividades-bim/{id}`: Consulta de una actividad propia.
- `PUT /api/actividades-bim/{id}` / `DELETE /api/actividades-bim/{id}`: Modificación y eliminación de actividad propia.
- `GET /api/actividades-bim/usuario/{id_usuario}`: Historial cronológico de eventos BIM del usuario.
- `GET /api/dashboard/resumen`: Endpoint políglota unificado con métricas de obras, presupuestos y actividad reciente.

---

## Pruebas y calidad de código

El proyecto cuenta con una suite integral de 31 pruebas unitarias y de integración en el backend, ejecutadas con bases SQLite en memoria y simulación aislada de MongoDB mediante `mongomock`.

### Ejecutar pruebas del backend

Para ejecutar los tests asegurando la resolución correcta de módulos:

**Opción 1 (desde la carpeta `backend`):**
```powershell
Set-Location backend
..\.venv\Scripts\python.exe -m pytest -q
Set-Location ..
```

**Opción 2 (desde la raíz del proyecto):**
```powershell
.\.venv\Scripts\python.exe -m pytest backend -o pythonpath=backend -q
```

### Ejecutar validaciones del frontend

Desde la carpeta `frontend-bimetrics`:

```powershell
# Verificación estática con ESLint
npm --prefix frontend-bimetrics run lint

# Compilación de producción con Vite
npm --prefix frontend-bimetrics run build
```

### Integración Continua (CI)

El flujo de GitHub Actions en `.github/workflows/quality-security.yml` valida automáticamente en cada push y PR:
- Ejecución de pruebas del backend con pytest.
- Validación del contrato OpenAPI mediante `openapi-spec-validator`.
- Auditoría de vulnerabilidades en dependencias Python con `pip-audit`.
- Linting y build de producción del frontend.
- Auditoría de seguridad en paquetes npm con `npm audit`.

---

## Solución de problemas comunes

### 1. `RuntimeError: Configura SECRET_KEY con un valor aleatorio y privado`
- Asegúrate de haber copiado `.env.example` a `.env` en la raíz del proyecto y de que `SECRET_KEY` tenga un valor configurado (mínimo 32 caracteres en producción).

### 2. `ModuleNotFoundError: No module named 'app'` al ejecutar pytest
- Pytest necesita reconocer el paquete `backend` en su ruta de importación. Ejecuta `pytest` situándote dentro de `backend/` o añade `-o pythonpath=backend` al comando ejecutado desde la raíz.

### 3. Error HTTP 503 en `/api/salud/mongodb`
- Si usas MongoDB Atlas, verifica que tu dirección IP pública actual esté autorizada en **Network Access** en la consola de Atlas.
- Si tu proveedor de internet bloquea resoluciones DNS SRV (`mongodb+srv`), define en `.env`:
  ```dotenv
  MONGO_DNS_SERVERS=1.1.1.1,8.8.8.8
  ```
- Si deseas trabajar offline, ejecuta `.\start_local.ps1` para usar MongoDB en Docker.

### 4. Error HTTP 403 con mensaje `"Origen no permitido"`
- Las solicitudes de mutación (`POST`, `PUT`, `DELETE`) validan el encabezado `Origin`. Comprueba que `CORS_ORIGIN` en `.env` contenga la URL exacta desde la que navegas (por ejemplo `http://localhost:5173`).

### 5. `HTTP 503` en `/api/salud/sql`
- Revisa las credenciales de conexión en `CATALOG_DATABASE_URL` y asegúrate de que el servicio MySQL esté en ejecución y con el esquema restaurado.

---

## Documentación técnica

En el directorio [`docs/`](docs/) se encuentran los documentos técnicos y legales del proyecto:

- [Contrato formal de la API (OpenAPI 3.0)](docs/api/openapi.yaml)
- [Arquitectura de API y control de acceso (RBAC)](docs/arquitectura/api-y-control-acceso.md)
- [Arquitectura de persistencia políglota (SQL + NoSQL)](docs/arquitectura/persistencia-poliglota.md)
- [Diccionario y esquema relacional de datos (CSV)](docs/diagramas/esquema_presupuestos_lucidchart.csv)
- [Política de tratamiento de datos personales](docs/legal/politica-tratamiento-datos.md)
- [Términos y condiciones de uso](docs/legal/terminos-condiciones.md)

---

## Seguridad

- **Variables confidenciales:** El archivo `.env` nunca debe subirse al control de versiones.
- **Manejo de contraseñas:** Todas las credenciales de usuario se almacenan con algoritmos de hashing seguros (`generate_password_hash` con Werkzeug).
- **Protección de cookies de sesión:** Las cookies de sesión están marcadas como `HttpOnly` y `SameSite=Lax`. En entornos de producción (`BIMETRICS_ENV=production`), se exige `SESSION_COOKIE_SECURE=1` sobre HTTPS.
- **Validación de entradas y saneamiento:** Se restringe la longitud de campos, tipos numéricos y tamaño máximo de carga (6 MB) para mitigar vectores de denegación de servicio.
