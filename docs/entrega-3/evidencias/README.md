# Evidencias de ejecución de BIMetrics

## MongoDB Atlas en vivo

BIMetrics respondió HTTP 200 y estado `ok` al consultar `/api/salud/mongodb` con el clúster real de Atlas. El catálogo SQL también respondió HTTP 200. Una solicitud de inicio de sesión con credenciales ficticias, enviada a través del frontend, devolvió el HTTP 401 esperado. [Ver respuestas verificadas](atlas-en-vivo.json)

## Demostración aislada de los casos de uso

Se ejecutaron la interfaz React y la API Flask del commit base [237e3f9](https://github.com/Alejandro-LP/BIMetrics/commit/237e3f9e796bb8829519a63b11b06ef90d048591). El navegador consumió respuestas de Flask mediante su cliente de pruebas. Se usaron SQLite en memoria, MongoDB simulado, cuentas de prueba y datos ficticios. Las capturas muestran resultados de la ejecución y no certifican conectividad con Atlas ni MySQL.

| Evidencia | Resultado |
| --- | --- |
| [01 · Inicio de sesión](01-inicio-sesion.jpg) | Pantalla de acceso de la aplicación. El informe de API confirma el registro, el inicio de sesión y el rechazo de una consulta sin sesión. |
| [02 · Presupuesto con AIU](02-presupuesto-aiu.jpg) | CU-02. 20 m a $45.000 COP por metro dan $900.000 de costo directo. Con AIU de 20 %, el total es $1.080.000 COP. |
| [03 · Presupuestos del proyecto](03-historial-proyecto.jpg) | CU-04. La interfaz lista el presupuesto duplicado. El informe confirma la duplicación y la consulta del historial. |
| [04 · Resultados de la API](04-resultados-api.jpg) | CU-01: alta, consulta, edición y baja por administración. CU-03: descargas PDF, DOCX y XLSX con HTTP 200. RBAC: escritura de catálogo como cliente rechazada con HTTP 403. |
| [Resultados en JSON](resultados-api.json) | Estados HTTP devueltos por Flask durante la verificación. |
| [Persistencia políglota en entorno aislado](persistencia-poliglota.json) | CRUD documental y respuesta del dashboard que combina SQL y MongoDB simulado. |

Los tres archivos exportados se comprobaron por su estructura. La evidencia de descargas corresponde a solicitudes autenticadas a la API. El documento [Entrega 3](../README.md) explica qué pasos del alcance inicial siguen pendientes.

