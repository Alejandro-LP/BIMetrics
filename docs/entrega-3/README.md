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

## Verificación reproducible

1. Sigue las [instrucciones de instalación](../../README.md#configuración), incluidas las dependencias del backend para PDF y Word.
2. En el directorio backend, ejecuta **python -m pytest -q**. Las pruebas usan SQLite en memoria y MongoDB simulado.
3. Inicia la aplicación siguiendo el [README principal](../../README.md#ejecución). Usa cuentas de prueba y abre un presupuesto para descargarlo.
4. En la demostración, muestra el rol de la cuenta y luego el resultado de cada caso. La [guía de evidencias](evidencias/README.md) explica qué acredita cada captura.

