# Entrega 3 de BIMetrics

- [Repositorio público](https://github.com/Alejandro-LP/BIMetrics)
- [Instalación y ejecución](../../README.md#configuración)
- [Contrato OpenAPI](../api/openapi.yaml)
- [Diagrama UML de casos de uso](casos-de-uso.svg)
- [Evidencias de ejecución](evidencias/README.md)

La aplicación usa React y Vite en el frontend y Flask en la API. SQLite almacena los datos operativos. El catálogo maestro usa MySQL en la configuración habitual y admite SQLite en el modo local. MongoDB almacena usuarios y actividad BIM. Java, Spring Boot y JWT formaban parte del diseño inicial.

## Seguridad implementada

- **Registro e inicio de sesión.** Werkzeug genera un hash de la contraseña. El sistema lo almacena en MongoDB y lo comprueba al autenticar. El registro público admite arquitectura, ingeniería y cliente.
- **Sesión.** Las rutas privadas exigen una cookie de sesión firmada por Flask, configurada con HttpOnly, SameSite=Lax y Secure en producción. Una consulta sin sesión recibe HTTP 401. Las escrituras requieren un origen permitido.
- **Roles.** Arquitectura e ingeniería gestionan presupuestos de proyectos accesibles. Cliente consulta proyectos compartidos. Administrador modifica el catálogo maestro y gestiona cuentas. La API valida el rol y el acceso al proyecto.

## Trazabilidad con la Entrega 1

### CU-01 · Gestión del catálogo
El administrador crea, consulta, edita y elimina partidas por API. El equipo técnico consulta partidas y variaciones desde la aplicación. El formulario para que el arquitecto administre el catálogo maestro, descrito en la Entrega 1, queda pendiente.

### CU-02 · Cálculo paramétrico
El equipo técnico crea una obra, agrega cantidades y partidas, y revisa el costo directo y el AIU. El presupuesto conserva el precio aplicado a cada partida. La agrupación por capítulos y el flujo específico de insumos inactivos quedan pendientes.

### CU-03 · Generación de documentos
La aplicación exporta PDF, Word y Excel. PDF y Word incluyen el desglose del cálculo. Quedan pendientes la firma digital certificada, la tabla por capítulos y el reintento automático de compilación.

### CU-04 · Historial y reutilización
La aplicación consulta los presupuestos de un proyecto y permite duplicarlos. La API admite un proyecto de destino existente y accesible. La copia aplica precios vigentes del destino y el original conserva los importes aplicados. Quedan pendientes el filtro por cliente o fechas, la creación de una obra al duplicar y el ajuste masivo de precios.

Los cuatro casos se demuestran con el alcance indicado. El docente debe confirmar si acepta los pasos pendientes como cambios de alcance.

## Trazabilidad con la Entrega 2 · Persistencia políglota

Esta revisión sigue la consigna de la Entrega 2 y enlaza cada requisito con el entregable, la implementación o una ejecución.

1. **Identificación de datos no estructurados.** La actividad BIM tiene campos comunes, como usuario, proyecto, origen y fecha, y un subdocumento flexible `detalles_bim`. Sus propiedades varían según el software o el evento, por ejemplo conteos, unidades y advertencias. La [justificación en PDF](../entregables/justificacion_persistencia_poliglota.pdf) describe el modelo documental y por qué estos campos se guardan en MongoDB.
2. **Configuración y conexión NoSQL.** PyMongo configura la conexión con `MONGO_URI` y selecciona las bases por dominio. `GET /api/salud/mongodb` ejecuta un ping. La configuración está en el [código de conexión](../../backend/app/database.py) y en la [guía de persistencia](../arquitectura/persistencia-poliglota.md). **Conexión a MongoDB Atlas verificada en vivo.** La aplicación devolvió HTTP 200 y estado `ok` en `/api/salud/mongodb`. [Evidencia de Atlas](evidencias/atlas-en-vivo.json)
3. **Persistencia políglota.** SQLite almacena proyectos, presupuestos y detalle. MySQL almacena el catálogo maestro en la configuración habitual. MongoDB almacena identidades, preferencias y actividad BIM. Las referencias lógicas `id_usuario` e `id_proyecto` relacionan los datos sin una clave foránea entre motores. [Mapa y justificación de los almacenes](../arquitectura/persistencia-poliglota.md)
4. **Lógica de negocio y endpoint mixto.** `GET /api/dashboard/resumen` reúne en la misma respuesta el número de proyectos y el presupuesto total consultados en SQL, junto con el perfil y la última actividad de MongoDB. En la prueba devolvió **1 proyecto, $1.080.000 COP y la actividad BIM recién actualizada**. [Servicio del dashboard](../../backend/app/services/dashboard.py) · [Respuesta de la API](evidencias/persistencia-poliglota.json)
5. **CRUD documental.** La API permite crear, leer, actualizar y eliminar actividades en `/api/actividades-bim`. La ejecución verificó **201, 200, 200 y 200**, respectivamente, y una consulta posterior a la eliminación devolvió **404**. Las pruebas cubren también los controles de propiedad y los campos editables. [Rutas](../../backend/app/routes/actividades_bim.py) · [Pruebas](../../backend/tests/test_actividades_bim.py) · [Evidencia](evidencias/persistencia-poliglota.json)
6. **Repositorio, README y evidencias.** El [README principal](../../README.md#ejecución) contiene los pasos de configuración y ejecución. La [guía técnica](../arquitectura/persistencia-poliglota.md) explica cómo verificar MongoDB, reproducir el CRUD y consultar el endpoint mixto.

**Alcance de la evidencia.** La prueba en vivo confirmó la conexión de BIMetrics al clúster real de Atlas y que el inicio de sesión vuelve a validar credenciales. El registro del CRUD y el endpoint mixto enlazado en los puntos 4 y 5 corresponde a una ejecución aislada anterior con SQLite en memoria y MongoDB simulado. Queda pendiente documentar el CRUD y la respuesta mixta contra Atlas en vivo.

## Verificación reproducible

1. Sigue las [instrucciones de instalación](../../README.md#configuración), incluidas las dependencias del backend para PDF y Word.
2. En el directorio backend, ejecuta **python -m pytest -q**. Las pruebas usan SQLite en memoria y MongoDB simulado.
3. Inicia la aplicación siguiendo el [README principal](../../README.md#ejecución). Usa cuentas de prueba y abre un presupuesto para descargarlo.
4. En la demostración, muestra el rol de la cuenta y luego el resultado de cada caso. La [guía de evidencias](evidencias/README.md) explica qué acredita cada captura.

