# ObraPresupuesto Colombia

Plataforma de gestión de presupuestos de obra para edificación en Colombia. Permite administrar un catálogo de
insumos, calcular presupuestos por actividad y reutilizar presupuestos anteriores.

**Stack:** Python 3.9+, Flask (API REST), SQLAlchemy, SQLite (MySQL opcional), MongoDB (NoSQL con PyMongo), HTML/CSS/JS con GSAP.

## Estructura

```
obrapresupuesto/
├── backend/
│   ├── app/
│   │   ├── __init__.py        # fábrica de la app (create_app)
│   │   ├── config.py          # configuración y variables de entorno
│   │   ├── database.py        # conexión a la base de datos
│   │   ├── models.py          # esquema (según el diagrama ER)
│   │   ├── errors.py          # errores JSON y CORS
│   │   ├── utils.py           # validaciones y utilidades
│   │   ├── routes/            # autenticación y endpoints por recurso
│   │   └── services/          # lógica de negocio (cálculo de presupuestos)
│   ├── scripts/poblar_bd.py   # carga una demo unica
│   ├── tests/test_api.py      # pruebas automáticas
│   ├── run.py                 # punto de entrada
│   └── requirements.txt
├── frontend/                  # landing, acceso y dashboard
│   ├── index.html             # landing pública
│   ├── login.html, registro.html, dashboard.html
│   ├── css/                   # estilos de sitio y dashboard
│   └── js/                    # sesión, formularios y dashboard
├── docs/
│   ├── diagramas/             # CSV para importar el ER en Lucidchart
│   └── sql/                   # esquema y ejemplo para MySQL
├── data/                      # aquí se guarda presupuestos.db (no se sube a git)
├── .env.example
└── .gitignore
```

## Puesta en marcha

Desde la raiz del proyecto, en PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
cd backend
python -m scripts.poblar_bd --reset
python run.py
```

Antes de iniciar, crea un archivo `.env` en la raíz y configura `SECRET_KEY` con una clave aleatoria privada (puedes generarla con `python -c "import secrets; print(secrets.token_hex(32))"`). Para desarrollo local servido por HTTP, agrega `SESSION_COOKIE_SECURE=0`; en producción HTTPS usa `SESSION_COOKIE_SECURE=1`. No subas `.env` al repositorio.

Abre http://127.0.0.1:5000 para entrar al landing, crear una cuenta o iniciar sesion. Elige Arquitecto o Ingeniero para editar presupuestos; Cliente tiene acceso de consulta. Desde el dashboard se pueden agregar insumos del catalogo y quitar partidas. El perfil permite actualizar nombre, correo y contrasena. Flask sirve las paginas y la API desde el mismo origen, por lo que no abras los HTML con doble clic.

Los proyectos guardan su ciudad y consultan primero el precio unitario registrado para esa ciudad. Un arquitecto puede crear un insumo desde el diálogo de partidas y cargar su precio local; las tarifas existentes son referencias ilustrativas y deben verificarse antes de usarlas. Las bases de datos antiguas reciben Bogotá como ciudad inicial para los proyectos existentes. Los presupuestos conservan el precio aplicado al momento de agregar cada partida.

## Pruebas

```bash
cd backend
python -m pytest -q
```

## Endpoints principales

| Recurso | Operaciones |
|---|---|
| `/api/auth` | registro por rol, login/logout, sesion y edicion de perfil |
| `/api/insumos` | listar (`?q=`), ver, crear, editar, eliminar |
| `/api/usuarios` | listar (`?rol=`), ver, crear, editar, eliminar |
| `/api/proyectos` | listar, crear, historial en `/<id>/presupuestos` |
| `/api/presupuestos` | listar, ver con detalle, crear (con o sin líneas) |
| `/api/presupuestos/<id>/calcular` | recalcula y guarda el costo total |
| `/api/presupuestos/<id>/duplicar` | copia el presupuesto con los costos vigentes |
| `/api/presupuestos/<id>/detalle` | agregar (`POST`) y quitar (`DELETE /<id_detalle>`) líneas |
| `/api/actividades-bim` | CRUD de telemetría e importaciones BIM; endpoint híbrido en `/usuario/<id>` |

## Persistencia Políglota (SQL + NoSQL con MongoDB)

BIMetrics implementa una arquitectura de **persistencia políglota** diseñada para resolver dos necesidades computacionales opuestas en proyectos de construcción y estimación BIM 5D:

1. **Núcleo Relacional Estructurado (SQL - SQLite / MySQL):**
   - Garantiza consistencia transaccional **ACID** para usuarios, perfiles RBAC, proyectos, catálogos de insumos y presupuestos oficiales.
   - Preserva la regla de negocio inmutable del valor histórico (`costo_unitario_aplicado`).

2. **Capa Documental Flexible (NoSQL - MongoDB con PyMongo):**
   - Colección: `actividades_bim`.
   - **Por qué NoSQL para importaciones y logs BIM:**
     * **Agilidad de Esquema (Schema Agility):** Las tablas de cantidades (.txt o .csv) exportadas de Revit o ArchiCAD contienen parámetros muy divergentes según la especialidad (estructural, hidrosanitaria, eléctrica) y versión del software. Un esquema relacional requeriría tablas EAV o cientos de columnas nulas.
     * **Jerarquía Natural de Datos:** Los cómputos BIM poseen estructuras anidadas (Fases, Niveles, Familias, Advertencias de cómputo) que se representan de forma limpia como subdocumentos JSON/BSON.
     * **Alto Rendimiento en Ingesta Append-Only:** Desacopla la auditoría y telemetría de importación sin generar bloqueos (`table locks`) sobre las tablas financieras principales.

### Configuración del Entorno NoSQL

En el archivo `.env` en la raíz del proyecto, define las variables de conexión:

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

#### 4. Ejecutar Pruebas Automatizadas

Para validar las operaciones CRUD NoSQL y el endpoint políglota:

```bash
cd backend
python -m pytest tests/test_actividades_bim.py -v
```

## Datos

La carga de demostracion crea un solo usuario, un proyecto y un presupuesto de viga con seis insumos. El total ilustrativo es $1.611.150 COP; no representa una cotizacion oficial. Desde `backend/`, ejecuta `python -m scripts.poblar_bd --reset` para reemplazar los datos por esta demo unica. El costo de cada insumo se copia al presupuesto (`costo_unitario_aplicado`), asi que cambiar el catalogo no altera presupuestos ya calculados.
