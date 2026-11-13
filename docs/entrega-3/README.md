# Cierre funcional y trazabilidad de casos de uso

Este documento describe los casos de uso implementados en BIMetrics y cómo demostrarlos. Las rutas de la API usan el prefijo `/api` y las operaciones privadas requieren una sesión activa.

## Casos de uso

| Caso | Funcionalidad | Control de acceso | Evidencia sugerida |
|---|---|---|---|
| CU-01. Cuenta y acceso | Registro, inicio y cierre de sesión, restablecimiento de contraseña, perfil y códigos de invitación de un solo uso. Las contraseñas se guardan con hash. | Sesión firmada; roles de administrador, arquitecto, ingeniero y cliente. | Registrar una cuenta de prueba, iniciar sesión y mostrar la sesión activa. |
| CU-02. Proyectos y colaboración | Crear, consultar y eliminar proyectos; compartir una obra mediante código compatible con el rol del invitado. | Arquitectura/ingeniería edita proyectos accesibles; cliente consulta; solo el propietario administra invitaciones y elimina la obra. | Crear una obra, generar un código, canjearlo desde otra cuenta y verificar el acceso concedido. |
| CU-03. Presupuesto de obra | Crear presupuesto, agregar partidas e insumos desde SQL, seleccionar variaciones, definir capítulos, añadir perfiles de mano de obra, retirar líneas, actualizar AIU, recalcular y duplicar dentro de la misma obra o en otra obra. | Las escrituras se restringen a perfiles profesionales autorizados y se valida el acceso a cada obra. El cliente tiene permisos de lectura. | Agregar una partida con variación y capítulo; mostrar subtotales, mano de obra y total recalculado. |
| CU-04. Catálogo y precios | Buscar catálogo SQL con tolerancia a errores; administrar partidas maestras, insumos activos/archivados y precios de referencia. | La administración del catálogo y de precios es exclusiva de administradores. El precio aplicado al presupuesto proviene del catálogo. | Buscar una partida, mostrar sus variaciones, y probar las operaciones administrativas con una cuenta autorizada. |
| CU-05. Importación BIM | Leer cómputos TXT exportados desde Revit o Archicad, previsualizar coincidencias y registrar la importación/actividad BIM. | Se requiere sesión y acceso al proyecto destino. | Importar un TXT de muestra, revisar la previsualización y confirmar la actividad registrada. |
| CU-06. Consulta y exportación | Consultar historial con filtros de cliente/fecha, ver presupuesto y descargar Excel, PDF o Word agrupados por capítulo. | La consulta se limita a proyectos accesibles; las exportaciones exigen sesión. | Filtrar por fechas y descargar cada formato. |
| CU-07. Actividad BIM y persistencia políglota | Guardar actividad con metadatos flexibles en MongoDB y combinar identidad/actividad documental con métricas SQL en el dashboard. | Sesión activa; cada actividad se protege por propietario y permisos administrativos. | Consultar `/api/salud/mongodb`, crear/leer/actualizar/eliminar una actividad y mostrar `/api/dashboard/resumen`. |

## Operaciones principales de API

- **Autenticación:** `POST /api/auth/registro`, `POST /api/auth/login`, `GET /api/auth/sesion`, `POST /api/auth/logout`, rutas de solicitud y aplicación de restablecimiento de contraseña.
- **Proyectos:** `GET/POST /api/proyectos`, `GET /api/proyectos/{id}/presupuestos?cliente=&desde=&hasta=`, rutas de invitación y `DELETE /api/proyectos/{id}`.
- **Presupuestos:** `GET/POST /api/presupuestos`, `GET /api/presupuestos/{id}`, agregar/eliminar detalle, agregar partida, cambiar AIU, recalcular, duplicar, importar TXT y descargar `/pdf`, `/word` o `/excel`.
- **Catálogo:** `GET/POST /api/partidas`, `GET/PUT/DELETE /api/partidas/{codigo}`, `GET /api/partidas/buscar` y `GET /api/partidas/{codigo}`.
- **Insumos:** `GET/POST /api/insumos`, `PUT/DELETE /api/insumos/{id}`, `PATCH /api/insumos/{id}/estado` y `PUT /api/insumos/precios/ajuste-masivo`.
- **Actividad documental:** CRUD en `/api/actividades-bim`; integración SQL + MongoDB en `GET /api/dashboard/resumen`.

El contrato ampliado se encuentra en [OpenAPI](../api/openapi.yaml). Puede abrirse con Swagger UI o Redoc para una demostración interactiva.

## Firma digital certificada

La exportación PDF/Word no incorpora una firma digital certificada. La aplicación no posee un certificado digital ni credenciales de un proveedor de firma. No debe presentarse la descarga de un archivo ni una imagen de firma como prueba de firma certificada. Para activar este caso se debe contratar/configurar un proveedor compatible, custodiar sus secretos en variables de entorno y validar su flujo de firma en un ambiente de pruebas.

## Lista de demostración

1. Inicia backend y frontend siguiendo el [README del repositorio](../../README.md#ejecución), con bases de datos configuradas.
2. Demuestra sesión y roles usando cuentas de prueba distintas: profesional, cliente y administrador.
3. Crea obra y presupuesto; añade una partida, variación, capítulo y mano de obra; recalcula y revisa AIU.
4. Demuestra que el cliente puede consultar y que una operación de escritura es rechazada.
5. Prueba historial con filtros, duplicación a otra obra, importación TXT y descargas Excel/PDF/Word.
6. Comprueba el estado SQL/MongoDB y muestra la respuesta combinada del dashboard.
7. Conserva capturas de estas ejecuciones con datos ficticios. Oculta tokens, contraseñas, correos personales, URI de conexión y códigos vigentes.

Las pruebas automatizadas incluidas usan bases aisladas o MongoDB simulado; demuestran comportamiento del código, pero no sustituyen una evidencia de conexión a los servicios de despliegue reales.
