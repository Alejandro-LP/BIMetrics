# BIMetrics - Plataforma SaaS de Presupuestos de Obra y Estimación BIM 5D

Plataforma web integral para la **gestión de presupuestos de edificación en Colombia** y **estimación paramétrica BIM 5D**. Permite administrar catálogos de insumos, importar cómputos métricos desde software BIM (Autodesk Revit y Graphisoft ArchiCAD), calcular presupuestos dinámicos por actividad y mantener trazabilidad mediante una **arquitectura de persistencia políglota** (SQL relacional + NoSQL documental).

**Stack:** Python 3.9+, Flask 3 (API REST), SQLAlchemy 2 (Core), SQLite / MySQL (SQL), MongoDB (NoSQL con PyMongo), HTML5/CSS3/JS Vanilla con GSAP.

---

## Estructura del Proyecto

```
bimetrics/
├── backend/
│   ├── app/
│   │   ├── __init__.py        # Fábrica de la app (create_app), registro de blueprints y seguridad
│   │   ├── config.py          # Configuración central y variables de entorno (.env)
│   │   ├── database.py        # Conexión híbrida: SQLAlchemy (SQL) + PyMongo (MongoDB)
│   │   ├── models.py          # Esquema relacional (MetaData según diagrama ER)
│   │   ├── errors.py          # Manejador centralizado de excepciones ErrorApi y CORS
│   │   ├── utils.py           # Validaciones numéricas, serializadores y utilidades
│   │   ├── routes/            # Blueprints REST (auth, insumos, presupuestos, proyectos, actividades_bim)
│   │   └── services/          # Lógica de dominio (cálculo presupuestal y CRUD NoSQL BIM)
│   ├── scripts/poblar_bd.py   # Script de carga de datos demo para pruebas
│   ├── tests/                 # Pruebas automatizadas (test_api.py, test_actividades_bim.py)
│   ├── run.py                 # Punto de entrada de la aplicación Flask
│   └── requirements.txt       # Dependencias oficiales del backend
├── frontend/                  # Interfaz de usuario (Vanilla JS, CSS modular)
│   ├── index.html             # Landing page pública
│   ├── login.html, registro.html, dashboard.html, perfil.html
│   ├── css/                   # Estilos del sitio y del dashboard
│   └── js/                    # Controladores de interfaz, llamadas a la API y animaciones
├── docs/                      # Diagramas entidad-relación y scripts DDL
├── data/                      # Almacén de base de datos SQLite local (ignorado en git)
├── .env.example               # Plantilla de variables de entorno (SQL + MongoDB)
└── .gitignore
```

---

## Puesta en Marcha

Desde la raíz del proyecto, en PowerShell:

```powershell
# 1. Crear y activar entorno virtual
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Instalar dependencias
pip install -r backend\requirements.txt

# 3. Configurar variables de entorno
# Copia .env.example como .env y ajusta tus claves:
Copy-Item .env.example .env

# 4. Poblar datos demostrativos en la base de datos relacional
cd backend
python -m scripts.poblar_bd --reset

# 5. Iniciar el servidor de desarrollo
python run.py
```

### Configuración del archivo `.env`

Antes de iniciar la aplicación en desarrollo o producción, define las siguientes variables en `.env`:

```dotenv
# Seguridad de sesión de Flask
SECRET_KEY=clave-secreta-aleatoria-generada-en-consola
SESSION_COOKIE_SECURE=0    # Usa 0 para desarrollo local HTTP; 1 para producción HTTPS

# Base Relacional SQL (SQLite por defecto, o MySQL)
DATABASE_URL=sqlite:///../data/presupuestos.db
# DATABASE_URL=mysql+pymysql://usuario:clave@localhost:3306/bimetrics_db

# Base Documental NoSQL (MongoDB - Logs de actividad e importaciones BIM)
MONGO_URI=mongodb://localhost:27017
MONGO_DB_NAME=bimetrics_nosql
```

Abre http://127.0.0.1:5000 para entrar a la plataforma:
- **Landing page**: Presentación general de la plataforma y propuesta de valor.
- **Roles admitidos**: `arquitecto`, `ingeniero`, `administrador` (edición y gestión completa) y `cliente` (modo consulta de solo lectura).
- **Dashboard interactivo**: Administración de proyectos, desglose de insumos y parametrización de presupuestos.
- **Perfil de usuario**: Edición de nombre, correo y credenciales.

---

## Endpoints Principales de la API

| Recurso | Método | Ruta | Descripción |
|---|---|---|---|
| `/api/salud` | GET | `/api/salud` | Healthcheck público del sistema |
| `/api/auth` | POST / GET / PUT | `/registro`, `/login`, `/logout`, `/sesion`, `/perfil` | Autenticación, sesión y perfil de usuario |
| `/api/insumos` | GET / POST / PUT / DELETE | `/api/insumos` (`?q=`), `/<id>` | CRUD de insumos y precios unitarios |
| `/api/usuarios` | GET / POST / PUT / DELETE | `/api/usuarios` (`?rol=`), `/<id>` | Administración RBAC de usuarios |
| `/api/proyectos` | GET / POST | `/api/proyectos`, `/<id>/presupuestos` | Proyectos y su historial presupuestal |
| `/api/presupuestos` | GET / POST | `/api/presupuestos`, `/<id>` | Consulta y creación de presupuestos |
| `/api/presupuestos` | POST | `/<id>/calcular` | Recalcula el costo total oficial en el backend |
| `/api/presupuestos` | POST | `/<id>/duplicar` | Duplica presupuesto tomando precios vigentes |
| `/api/presupuestos` | POST / DELETE | `/<id>/detalle`, `/<id>/detalle/<id_det>` | Gestión de líneas y partidas presupuestales |
| **`/api/actividades-bim`** | **GET** | **`/api/actividades-bim/usuario/<id>`** | **Endpoint Híbrido Políglota (Perfil SQL + Logs NoSQL)** |
| `/api/actividades-bim` | POST / GET / PUT / DELETE | `/api/actividades-bim`, `/<id_actividad>` | CRUD de logs e importaciones BIM en MongoDB |

---

## Persistencia Políglota (SQL + NoSQL con MongoDB)

BIMetrics implementa una arquitectura de **persistencia políglota** (*Polyglot Persistence*) diseñada para resolver dos necesidades computacionales opuestas en proyectos de construcción y estimación BIM 5D:

1. **Núcleo Relacional Estructurado (SQL - SQLite / MySQL):**
   - Garantiza consistencia transaccional **ACID** para usuarios, perfiles RBAC, proyectos, catálogos de insumos y presupuestos oficiales.
   - Preserva la regla de negocio inmutable del valor histórico (`costo_unitario_aplicado`).

2. **Capa Documental Flexible (NoSQL - MongoDB con PyMongo):**
   - Colección: `actividades_bim`.
   - **Por qué NoSQL para importaciones y logs BIM:**
     * **Agilidad de Esquema (Schema Agility):** Las tablas de cantidades (.txt o .csv) exportadas de Revit o ArchiCAD contienen parámetros muy divergentes según la especialidad (estructural, hidrosanitaria, eléctrica) y versión del software. Un esquema relacional requeriría tablas EAV o cientos de columnas nulas.
     * **Jerarquía Natural de Datos:** Los cómputos BIM poseen estructuras anidadas (Fases, Niveles, Familias, Advertencias de cómputo) que se representan de forma limpia como subdocumentos JSON/BSON sin `JOIN`s costosos.
     * **Alto Rendimiento en Ingesta Append-Only:** Desacopla la auditoría y telemetría de importación sin generar bloqueos (`table locks`) sobre las tablas financieras principales.
     * **Aislamiento Transaccional (ACID vs. BASE):** Una discrepancia de formato en un archivo CAD/BIM nunca bloquea las transacciones contables del presupuesto.

### Configuración del Entorno NoSQL

En el archivo `.env` en la raíz del proyecto:

```dotenv
MONGO_URI=mongodb://localhost:27017
MONGO_DB_NAME=bimetrics_nosql
```

> **Para iniciar MongoDB rápidamente con Docker:**
> ```bash
> docker run -d --name bimetrics-mongo -p 27017:27017 -v mongo_data:/data/db mongo:7.0
> ```

### Estructura del Documento `actividades_bim`

```json
{
  "_id": "67144e59f2a9e34c9c1b9b1a",
  "id_usuario": 1,
  "id_proyecto": 3,
  "tipo_evento": "importacion_revit_txt",
  "software_origen": "Autodesk Revit 2024",
  "nombre_archivo": "Computos_Estructural_Vigas.txt",
  "estado": "completado",
  "fecha_registro": "2026-10-19T21:00:00+00:00",
  "detalles_bim": {
    "num_elementos": 42,
    "volumen_total_m3": 18.75,
    "categorias_extraidas": ["Structural Framing", "Concrete Beams"],
    "advertencias": [
      "Línea 12: acero 3/8 pulg sin longitud explícita, se asigna estándar de 6m"
    ]
  }
}
```

### Pasos para Probar el Endpoint Políglota Híbrido

El endpoint híbrido combina en un único payload el perfil estructurado del usuario desde SQL y sus últimas 10 actividades/importaciones desde MongoDB.

#### 1. Iniciar la aplicación backend

```powershell
cd backend
python run.py
```

#### 2. Registrar una actividad BIM en MongoDB (POST)

En PowerShell:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:5000/api/actividades-bim" -Method Post -ContentType "application/json" -Body (@{
    id_usuario = 1
    tipo_evento = "importacion_revit_txt"
    software_origen = "Autodesk Revit 2024"
    nombre_archivo = "Cómputos_VigaZapata_10m.txt"
    estado = "completado"
    detalles_bim = @{
        num_elementos = 6
        volumen_total_m3 = 0.95
        acero_kilos = 92.4
        tiempo_procesamiento_ms = 85
    }
} | ConvertTo-Json -Depth 5)
```

O con `curl`:

```bash
curl -X POST http://127.0.0.1:5000/api/actividades-bim \
  -H "Content-Type: application/json" \
  -d '{
    "id_usuario": 1,
    "tipo_evento": "importacion_revit_txt",
    "software_origen": "Autodesk Revit 2024",
    "nombre_archivo": "Cómputos_VigaZapata_10m.txt",
    "estado": "completado",
    "detalles_bim": {
      "num_elementos": 6,
      "volumen_total_m3": 0.95,
      "acero_kilos": 92.4,
      "tiempo_procesamiento_ms": 85
    }
  }'
```

#### 3. Consultar el Endpoint Híbrido (GET)

```bash
curl -X GET http://127.0.0.1:5000/api/actividades-bim/usuario/1
```

**Respuesta unificada (SQL + NoSQL):**

```json
{
  "usuario": {
    "id_usuario": 1,
    "nombre_completo": "Demo Arquitecto",
    "email": "demo@ejemplo.com",
    "rol": "arquitecto"
  },
  "resumen_bim": {
    "total_actividades_recientes": 1,
    "software_mas_frecuente": "Autodesk Revit 2024",
    "ultima_actividad": "2026-10-19T21:05:12+00:00"
  },
  "actividades_recientes": [
    {
      "id": "67144e59f2a9e34c9c1b9b1a",
      "id_usuario": 1,
      "id_proyecto": null,
      "tipo_evento": "importacion_revit_txt",
      "software_origen": "Autodesk Revit 2024",
      "nombre_archivo": "Cómputos_VigaZapata_10m.txt",
      "estado": "completado",
      "fecha_registro": "2026-10-19T21:05:12+00:00",
      "fecha_actualizacion": "2026-10-19T21:05:12+00:00",
      "detalles_bim": {
        "num_elementos": 6,
        "volumen_total_m3": 0.95,
        "acero_kilos": 92.4,
        "tiempo_procesamiento_ms": 85
      }
    }
  ]
}
```

---

## Pruebas Automatizadas

Para validar las operaciones CRUD NoSQL y el endpoint políglota con simulación determinística en memoria (`mongomock`):

```bash
cd backend
python -m pytest tests/test_actividades_bim.py -v
```

---

## Datos de Demostración

La carga de demostración crea un usuario, un proyecto y un presupuesto de viga con seis insumos base. El total ilustrativo es **$1.611.150 COP** (concreto 3000 PSI 0,95 m³; acero 1/2" 8 varillas; acero 3/8" 10 varillas; alambre negro 3 kg; oficial 2 jornales; ayudante 3 jornales).

Para restablecer la base de datos a este estado inicial, ejecuta desde `backend/`:

```bash
python -m scripts.poblar_bd --reset
```
