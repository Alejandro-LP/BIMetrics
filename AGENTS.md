# AGENTS.md - ObraPresupuesto Colombia

Contexto del proyecto para agentes de programación (Codex y similares). Léelo completo antes de modificar código.

## 1. Qué es este proyecto

Plataforma web para **gestionar presupuestos de obra de edificación en Colombia**. Es un proyecto
académico de Ingeniería de Sistemas; el profesor exige que el **backend sea Python**.

Idea central: hay un **catálogo de insumos** (materiales, mano de obra, equipos) con su costo unitario. Un
**presupuesto** se arma eligiendo insumos y cantidades; el sistema calcula el costo total (cálculo paramétrico).
Los presupuestos se guardan por proyecto, se pueden **duplicar/reutilizar** y se pueden generar como documento.

Ejemplo de referencia: "Viga entre zapatas (10 m), sección 0,30 x 0,30 m" con los precios base del catálogo da
**$1.611.150 COP** (concreto 3000 PSI 0,95 m3; acero 1/2" 8 varillas; acero 3/8" 10 varillas; alambre negro 3 kg;
oficial 2 jornales; ayudante 3 jornales). Úsalo como caso de prueba.

## 2. Actores y casos de uso

| Actor | Casos de uso |
|---|---|
| Arquitecto | CU-01 Gestión de catálogos e insumos; CU-02 Cálculo paramétrico de presupuestos; CU-03 Generación automatizada de documentos; CU-04 Consulta y reutilización de historial |
| Ingeniero | Mismo perfil técnico que el arquitecto; también puede ser responsable de proyectos |
| Administrador | Administración global de insumos y usuarios |
| Cliente | Consulta y descarga de presupuestos (solo lectura) |

Roles válidos en la base: `arquitecto`, `ingeniero`, `administrador`, `cliente`.

## 3. Stack

- Backend: Python 3.9+, Flask 3, SQLAlchemy 2 (**Core con `text()`, sin ORM**), python-dotenv, pytest.
- Base de datos: **SQLite** por defecto (`data/presupuestos.db`); **MySQL** opcional vía `DATABASE_URL`.
- Frontend: HTML, CSS y JavaScript **vanilla**, sin build ni frameworks; GSAP por CDN para animaciones.

## 4. Estructura

```
backend/
  app/
    __init__.py       create_app(): registra errores, blueprints y crea tablas
    config.py         DB_URL, CORS_ORIGIN, ROLES (lee variables de entorno y .env)
    database.py       engine de SQLAlchemy
    models.py         esquema (MetaData) y tupla TABLAS en orden padre -> hijo
    errors.py         ErrorApi, manejadores JSON y cabeceras CORS
    utils.py          pedir(), numero(), obtener(), en_uso(), filas(), una(), limpiar()
    routes/           blueprints de auth, insumos, usuarios, proyectos y presupuestos
    services/         lógica de negocio (presupuestos.py: recalcular, agregar_linea, presupuesto_completo)
  scripts/poblar_bd.py  carga una demo unica
  tests/test_api.py     pruebas con base temporal
  run.py                punto de entrada
frontend/               index.html, css/styles.css, js/script.js (estático)
docs/                   diagramas/ (CSV para Lucidchart), sql/ (esquema y ejemplo para MySQL)
data/                   aquí vive presupuestos.db (ignorado por git)
```

## 5. Modelo de datos

```
USUARIOS(id_usuario PK, nombre_completo, email UNIQUE, rol)
CREDENCIALES(id_usuario PK/FK, password_hash)
PROYECTOS(id_proyecto PK, id_usuario FK, nombre_obra, cliente)
PRESUPUESTOS(id_presupuesto PK, id_proyecto FK, fecha_calculo, costo_total)
INSUMOS(id_insumo PK, nombre_insumo UNIQUE, unidad_medida, costo_unitario)
DETALLE_PRESUPUESTO(id_detalle PK, id_presupuesto FK, id_insumo FK, cantidad, costo_unitario_aplicado)
```

Relaciones: USUARIOS 1:N PROYECTOS; PROYECTOS 1:N PRESUPUESTOS; PRESUPUESTOS N:M INSUMOS mediante
DETALLE_PRESUPUESTO.

**Invariante clave:** `costo_unitario_aplicado` es una **copia** del costo del insumo en el momento de agregarlo.
Cambiar `INSUMOS.costo_unitario` después **no debe alterar** presupuestos ya calculados. Solo al **duplicar** un
presupuesto se toman los costos vigentes del catálogo.

`PRESUPUESTOS.costo_total = SUM(cantidad * costo_unitario_aplicado)` y lo calcula el backend (`recalcular`).

## 6. API REST (prefijo `/api`)

| Ruta | Descripción |
|---|---|
| `GET /salud` | Comprobacion publica de estado |
| `POST /auth/registro`, `POST /auth/login` | Registro e inicio de sesion |
| `GET /auth/sesion`, `POST /auth/logout`, `PUT /auth/perfil` | Consultar/cerrar sesion y editar perfil |
| `GET/POST /insumos`, `GET/PUT/DELETE /insumos/<id>` | CRUD de insumos (`?q=` filtra por nombre) |
| `GET/POST /usuarios`, `GET/PUT/DELETE /usuarios/<id>` | CRUD de usuarios (`?rol=` filtra) |
| `GET/POST /proyectos`, `GET /proyectos/<id>/presupuestos` | Proyectos e historial |
| `GET/POST /presupuestos`, `GET /presupuestos/<id>` | Listar (`?id_proyecto=`), crear (con `detalle` opcional) y ver con líneas |
| `POST /presupuestos/<id>/calcular` | Recalcula y guarda `costo_total` |
| `POST /presupuestos/<id>/duplicar` | Copia a mismo u otro proyecto (`{"id_proyecto": n}` opcional) |
| `POST /presupuestos/<id>/detalle`, `DELETE /presupuestos/<id>/detalle/<id_detalle>` | Agregar/quitar líneas |

Errores: JSON `{"error": "mensaje"}` con 400 (datos inválidos), 404 (no existe), 409 (duplicado o en uso).

## 7. Comandos

Desde la raíz del proyecto:

```bash
python -m venv venv && venv\Scripts\activate      # Mac/Linux: source venv/bin/activate
pip install -r backend/requirements.txt
cd backend
python -m scripts.poblar_bd --reset               # datos ficticios en data/presupuestos.db
python run.py                                     # API en http://127.0.0.1:5000
python -m pytest -q                               # pruebas (deben pasar siempre)
```

## 8. Convenciones de código

- **Idioma:** nombres de dominio, tablas, columnas, mensajes de error y comentarios en **español**. Tablas en
  MAYÚSCULAS, columnas en `snake_case`.
- **SQL portable:** debe funcionar en SQLite **y** MySQL. No uses funciones ni sintaxis exclusivas de un motor.
- **Transacciones:** usa `with engine.begin() as con:` para escribir (hace commit o rollback solo) y
  `engine.connect()` para leer.
- **Errores:** lanza `ErrorApi(codigo, mensaje)`; no devuelvas errores a mano en cada ruta.
- **Validación:** entradas con `pedir([...])` y `numero(...)`. Cantidades `> 0`, costos `>= 0`.
- **Capas:** las rutas validan y responden; la lógica de negocio va en `services/`.
- **Pruebas:** cada endpoint nuevo lleva su prueba en `tests/`. La base de pruebas usa `DATABASE_URL` temporal,
  fijada **antes** de importar `app`. Ejecuta `python -m pytest -q` antes de dar una tarea por terminada.
- **Dinero:** pesos colombianos (COP), enteros o con `DECIMAL(14,2)`. En pantalla se formatea `es-CO`
  (`$1.611.150`).

## 9. Frontend

- Frontend en HTML, CSS y JavaScript vanilla, sin build ni framework.
- Identidad visual: fondo marfil, tarjetas blancas, verde bosque para acciones principales y acento terracota.
- Fuentes DM Sans y Manrope; conserva el diseno adaptable y `prefers-reduced-motion`.
- Flask sirve landing (`/`), login (`/login`), registro (`/registro`) y dashboard protegido (`/dashboard`).
- Las llamadas al backend usan el mismo origen y cookie de sesion; no abras las paginas con doble clic.

## 10. Datos

- La demo (`scripts/poblar_bd.py`) contiene un usuario, un proyecto y un presupuesto de viga con seis insumos;
  el total ilustrativo es $1.611.150 COP. No son precios oficiales.
- Los precios de demostración son ilustrativos; deben validarse por ciudad o región y fecha antes de usarlos como cotización. Los costos pueden variar en Colombia. Las cantidades por actividad también son ilustrativas y no provienen de una fuente verificada.
## 11. Estado y pendientes

Hecho: API REST, carga de demo unica, registro/login con sesion Flask, landing y dashboard conectado a la API.

Pendiente:
1. Generacion de documentos PDF/Excel del presupuesto.
2. Limitar proyectos y presupuestos por usuario y completar permisos administrativos por rol; el rol cliente ya es de solo lectura.
3. Recuperacion de contrasena y verificacion de correo.
4. Columna `categoria` en `INSUMOS` para desglosar materiales, mano de obra y equipos.
5. Asistente opcional para sugerir insumos a partir de una descripcion.

## 12. Reglas para el agente

- Haz cambios pequeños y enfocados; no reescribas módulos que no tocan la tarea.
- **No calcules totales en el frontend ni con IA**: el único cálculo oficial es `recalcular` en el backend.
- No borres insumos que estén en uso ni rompas el invariante de `costo_unitario_aplicado`.
- Si cambias el esquema, actualiza `models.py`, `scripts/poblar_bd.py`, `docs/sql/` y las pruebas.
- No subas `.env`, claves de API ni archivos `.db`. Las claves van solo en el backend, nunca en el frontend.
- No agregues dependencias nuevas sin necesidad; si lo haces, actualiza `backend/requirements.txt`.
- Si algo es ambiguo, pregunta antes de asumir; no inventes datos oficiales (precios, normas, fuentes).
