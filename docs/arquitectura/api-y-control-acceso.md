# API y control de acceso de BIMetrics
**Versión:** 2.0  
**Fecha:** 5 de noviembre de 2026

Este documento describe las rutas actuales de la API, el mecanismo de autenticación, la autorización por roles y la relación con los casos de uso del documento inicial. Describe el comportamiento observado en el código; no implica que las funcionalidades señaladas como pendientes estén implementadas.

## 1. Convenciones

- Prefijo de la API: `/api`.
- Formato de intercambio: JSON, salvo las descargas de Excel.
- Las rutas privadas usan una sesión Flask transportada mediante cookie.
- En el frontend, las solicitudes envían la cookie con `credentials: include`.
- Los errores se devuelven como JSON con una propiedad `error`.
- Códigos comunes: `400` datos inválidos, `401` sesión requerida o inválida, `403` permiso insuficiente, `404` recurso no encontrado, `409` conflicto y `503` dependencia no disponible.

## 2. Autenticación

| Método | Ruta | Acceso | Descripción |
|---|---|---|---|
| `POST` | `/api/auth/registro` | Público | Crea una cuenta permitida y abre una sesión. Requiere `nombre_completo`, `email`, `password`, `rol` y `autoriza_datos: true`. |
| `POST` | `/api/auth/login` | Público | Comprueba correo y contraseña y crea una sesión. |
| `GET` | `/api/auth/sesion` | Sesión | Devuelve el perfil de la sesión. |
| `POST` | `/api/auth/logout` | Público | Limpia la sesión actual. |
| `PUT` | `/api/auth/perfil` | Sesión | Actualiza el perfil tras verificar la contraseña actual. |
| `GET` | `/api/auth/preferencias` | Sesión | Consulta preferencias del usuario actual. |
| `PUT` | `/api/auth/preferencias` | Sesión | Actualiza las preferencias del usuario actual. |

Las contraseñas se procesan con las funciones de hash de Werkzeug. La API no debe devolver ni registrar contraseñas ni sus hashes.

## 3. Matriz de roles y permisos

Roles registrados en la aplicación: `cliente`, `arquitecto`, `ingeniero` y `administrador`.

| Capacidad | Cliente | Arquitecto | Ingeniero | Administrador |
|---|---:|---:|---:|---:|
| Consultar rutas autenticadas de negocio | Sí | Sí | Sí | Sí |
| Crear o modificar mediante rutas de negocio | No | Sí | Sí | Sí |
| Crear proyectos y presupuestos | No | Sí | Sí | Sí |
| Consultar/gestionar sus proyectos accesibles | Lectura | Sí | Sí | Sí* |
| Consultar y modificar usuarios (`/api/usuarios`) | No | No | No | Sí |
| Consultar actividad propia | Sí | Sí | Sí | Sí |
| Consultar actividad de otro usuario | No | No | No | Sí |
| Asignar el rol administrador | No | No | No | Sí |

\* La administración global de proyectos no se debe inferir: las operaciones de proyectos y presupuestos validan propietario o colaboración. El rol administrador no sustituye automáticamente esos permisos de recurso.

El control de acceso actual es principalmente una regla general: el rol `cliente` puede consultar, pero no enviar operaciones de escritura. Las rutas administrativas de usuarios y algunas consultas de actividad aplican reglas específicas para `administrador`. Arquitecto e ingeniero tienen permisos equivalentes en el control global actual.

## 4. Rutas funcionales

### 4.1 Proyectos

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/api/proyectos` | Lista proyectos propios y compartidos. |
| `POST` | `/api/proyectos` | Crea proyecto; requiere `nombre_obra`. |
| `GET` | `/api/proyectos/{id}/presupuestos` | Consulta el historial presupuestario del proyecto accesible. |
| `POST` | `/api/proyectos/{id}/colaboradores` | Agrega colaborador; requiere `email`. |
| `DELETE` | `/api/proyectos/{id}` | Elimina un proyecto propio. |

### 4.2 Insumos y catálogo

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/api/insumos?q={texto}&ciudad={ciudad}` | Busca insumos operativos. |
| `GET` | `/api/insumos/{id}` | Consulta un insumo. |
| `POST` | `/api/insumos` | Crea insumo o precio local; requiere `nombre_insumo`, `unidad_medida`, `costo_unitario`. |
| `PUT` | `/api/insumos/{id}` | Actualiza un insumo. |
| `DELETE` | `/api/insumos/{id}` | Elimina un insumo si no está en uso. |
| `GET` | `/api/partidas?limit=50&offset=0` | Consulta el catálogo maestro SQL paginado. |
| `GET` | `/api/partidas/buscar?q={texto}` | Busca partidas. |
| `GET` | `/api/partidas/{codigo}` | Consulta detalle y variaciones de una partida. |

El catálogo maestro expuesto por `/api/partidas` es de solo lectura en la API actual. Su carga se realiza mediante scripts de importación, no mediante operaciones CRUD de administración desde la aplicación.

### 4.3 Presupuestos

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/api/presupuestos?id_proyecto={id}` | Lista presupuestos visibles; el filtro de proyecto es opcional. |
| `POST` | `/api/presupuestos` | Crea presupuesto; requiere `id_proyecto` y opcionalmente `detalle`. |
| `GET` | `/api/presupuestos/{id}` | Consulta el presupuesto accesible y su detalle. |
| `POST` | `/api/presupuestos/{id}/detalle` | Agrega insumo y, opcionalmente, `lineas_mano_obra`. |
| `DELETE` | `/api/presupuestos/{id}/detalle/{detalle_id}` | Elimina una línea. |
| `POST` | `/api/presupuestos/{id}/calcular` | Recalcula el total. |
| `POST` | `/api/presupuestos/{id}/duplicar` | Duplica presupuesto usando precios vigentes del destino. |
| `GET` | `/api/presupuestos/{id}/excel` | Descarga el presupuesto en formato XLSX. |

### 4.4 Actividad BIM y resumen mixto

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/api/actividades-bim` | Crea actividad BIM del usuario autenticado. |
| `GET` | `/api/actividades-bim/{id}` | Consulta actividad propia; administrador puede consultar según reglas del servicio. |
| `PUT` | `/api/actividades-bim/{id}` | Actualiza campos permitidos de una actividad propia. |
| `DELETE` | `/api/actividades-bim/{id}` | Elimina una actividad propia. |
| `GET` | `/api/actividades-bim/usuario/{id_usuario}?limite=10` | Consulta perfil e historial reciente autorizado. |
| `GET` | `/api/dashboard/resumen` | Combina métricas SQL con identidad y actividad BIM de MongoDB. |

## 5. Casos de uso: trazabilidad del documento inicial

El documento inicial se conserva como referencia de la problemática y de los objetivos, pero su stack Java/Spring/JWT y algunas funciones documentales no describen la aplicación actual. Se actualiza la especificación técnica a Flask, sesiones, SQLAlchemy, SQLite/MySQL y MongoDB.

| Caso original | Estado actual | Ajuste necesario para describir la aplicación real |
|---|---|---|
| CU-01 Gestión de catálogo de insumos | Parcial | La aplicación consulta partidas del catálogo MySQL y permite gestionar insumos operativos. La API de partidas es solo lectura; no hay CRUD de administración del catálogo maestro. La carga se realiza con scripts. |
| CU-02 Cálculo paramétrico de presupuestos | Parcial | Se crean proyectos y presupuestos, se agregan líneas, se recalculan totales y se conservan costos aplicados. La estructura actual no implementa capítulos constructivos ni el cálculo de coeficientes AIU descritos originalmente. |
| CU-03 Generación de documentos | Parcial | La aplicación exporta presupuestos a Excel (XLSX). No se encontró exportación PDF/Word con firma digital ni reintentos de compilación. |
| CU-04 Consulta y reutilización de historial | Parcial | Se consulta historial de presupuestos por proyecto y se permite duplicarlos. No se encontraron filtros de historial por cliente o rango de fechas como los descritos en el documento inicial. |

### 5.1 Casos actualizados para la versión actual

**CU-A01: Gestionar cuenta y sesión.** Una persona puede registrarse con rol permitido, iniciar sesión, consultar su perfil y cerrar sesión. El sistema almacena un hash de contraseña y mantiene la identidad en la sesión.

**CU-A02: Gestionar proyectos.** Una persona autenticada crea proyectos y consulta los propios o compartidos. Las operaciones de recursos comprueban el propietario o la colaboración.

**CU-A03: Preparar y reutilizar presupuestos.** Una persona autorizada crea un presupuesto, agrega insumos y mano de obra disponible, consulta el total, lo recalcula, lo duplica y descarga una hoja XLSX.

**CU-A04: Consultar catálogo y sugerencias.** La persona consulta partidas y variaciones del catálogo SQL, selecciona insumos y recibe sugerencias de perfiles de mano de obra basadas en reglas de texto y disponibilidad de tarifas locales.

**CU-A05: Consultar actividad BIM.** La aplicación registra eventos con metadatos flexibles en MongoDB y valida la identidad y el acceso al proyecto relacionado.

**CU-A06: Consultar dashboard combinado.** La persona autenticada consulta métricas operativas SQL junto con su perfil y actividad BIM desde MongoDB.

## 6. Gaps y criterios de cierre

1. Publicar un contrato OpenAPI machine-readable para esta API o mantener este documento sincronizado con cambios de rutas y esquemas.
2. Definir si CU-01 requiere crear y editar el catálogo maestro desde la interfaz; hoy la API de partidas es de lectura.
3. Confirmar si capítulos constructivos y AIU siguen siendo requisitos. Si se mantienen, especificar reglas, porcentajes y redondeo antes de implementarlos.
4. Definir si la exportación XLSX satisface CU-03 o si se requiere PDF/Word y firma digital.
5. Definir filtros exactos para el historial si cliente y fechas siguen en alcance.
6. Añadir una demostración por caso actualizado: actor, datos de prueba, paso ejecutado y resultado esperado. No afirmar cobertura de todos los casos originales hasta resolver estos gaps.

## 7. Seguridad de sesión

La sesión se configura con cookie `HttpOnly` y `SameSite=Lax`; `Secure` se activa mediante `SESSION_COOKIE_SECURE=1` al servir por HTTPS. `SECRET_KEY` es obligatoria. Las solicitudes de escritura deben incluir `Origin` y coincidir con uno de los valores de `CORS_ORIGIN`; las solicitudes sin origen o con un origen diferente se rechazan. Los clientes no navegador que usen sesiones también deben enviar el origen configurado.

La creación administrativa de cuentas exige una contraseña de al menos 10 caracteres, que se almacena como hash. La actualización administrativa puede incluir opcionalmente `password` para reemplazarla; si se envía, también se valida y hashea.

