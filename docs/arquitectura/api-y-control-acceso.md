# API y control de acceso de BIMetrics

## Contrato y ejecución

El [contrato OpenAPI](../api/openapi.yaml) describe las operaciones HTTP, sus entradas, sus respuestas y la autenticación por cookie. Las rutas empiezan por `/api`. Los errores se devuelven como JSON y las exportaciones como archivos.

Sigue las [instrucciones de ejecución](../../README.md#ejecución). Consulta el [cierre de la Entrega 3](../entrega-3/README.md) para ver la trazabilidad con los cuatro casos originales y sus evidencias.

## Sesión y permisos

El registro y el inicio de sesión establecen una cookie de sesión firmada por Flask. En clientes HTTP, conserva y reenvía la cookie para las rutas privadas. Las escrituras requieren un encabezado `Origin` que coincida con el valor autorizado en `CORS_ORIGIN`. En producción, activa HTTPS y `SESSION_COOKIE_SECURE=1`.

- **Arquitectura e ingeniería** gestionan proyectos y presupuestos propios o compartidos.
- **Cliente** consulta los recursos de negocio accesibles. Las escrituras de presupuesto y catálogo se rechazan.
- **Administrador** mantiene el catálogo maestro y administra cuentas. Las operaciones sobre proyectos siguen comprobando el acceso al recurso.

Los errores `401`, `403` y `404` permiten distinguir sesión ausente, permiso insuficiente y recurso inexistente o fuera del alcance de la cuenta.

## Operaciones para la demostración

- **Sesión:** `POST /auth/registro`, `POST /auth/login`, `GET /auth/sesion` y `POST /auth/logout`.
- **Catálogo:** `GET /partidas`, `POST /partidas`, `PUT /partidas/{codigo}` y `DELETE /partidas/{codigo}`. Los cambios requieren el rol administrador.
- **Presupuesto:** `POST /proyectos`, `POST /presupuestos`, `POST /presupuestos/{id}/partidas`, `PUT /presupuestos/{id}/aiu` y `GET /presupuestos/{id}`.
- **Documentos:** `GET /presupuestos/{id}/pdf`, `/word` y `/excel`. PDF y Word requieren instalar las dependencias declaradas en el backend.
- **Historial:** `GET /proyectos/{id}/presupuestos` y `POST /presupuestos/{id}/duplicar`.
- **Persistencia combinada:** `GET /dashboard/resumen` integra datos operativos SQL y actividad BIM de MongoDB.

