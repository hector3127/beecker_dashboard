# Integración selectiva de versión 5 — 23/10/2026

Origen: `beecker_dashboard-main (5) (1).zip`.
Destino: `beecker_dashboard-main (4) (1)/beecker_dashboard-main`.
Respaldo previo: `.integration-backups/20261023-version5/` (fuentes, SQLite y manifiesto).

## Facturación: conciliación de los cortes guardados

Rango idéntico: 01/01/2026–31/12/2026. Columna G para fecha y H para importe.
Estados facturados: Invoiced, Invoiced Factoring, Collected y Collected Factoring.

| Corte (UTC) | Registros facturados | Importe |
|---|---:|---:|
| 21/10/2026 05:27 | 735 | $1,950,326.71 |
| 23/10/2026 17:55 | 741 | $2,006,482.71 |
| Diferencia | +6 | +$56,156.00 |

El aumento procede de cambios de la fuente, no del formateador ni del ZIP:
- Estafeta / EST-MX-AMS-008 / TYM.EST.002: dos filas Invoiced por $15,116.50 cada una, fecha 30/11/2026 (+$30,233.00).
- Arca Continental México / ARC-MX-AER-013 / AER.SBM.006: $5,604.97, fecha 13/10/2026.
- Heineken Mexico / HEI-MX-AER-105 / AER.MCC.005: tres filas Invoiced Factoring, $2,802.49 + $5,604.97 + $11,910.57 (+$20,318.03).

Los demás cambios son traspasos Invoiced→Collected, ajustes de día y cambios de ID sin diferencia neta de facturación.
La presentación compacta muestra 2M por truncamiento; el importe exacto sigue siendo $2,006,482.71.

**Validación de datos pendiente:** las filas 696 y 737 del snapshot DataRevenue son idénticas en sus nueve columnas: Estafeta, fecha 30/11/2026, 320 horas, $15,116.50. No hay identificador de factura que permita decidir si son cargos distintos. Si una sobra, el exceso sería $15,116.50 y el total $1,991,366.21. No se borraron filas ni se cambió la regla de suma. La fecha de noviembre entra en el rango anual seleccionado aunque sea futura.

### Revisión adicional de filas idénticas

El corte actual contiene **34 grupos** de filas facturadas de 2026 idénticas en las nueve columnas disponibles. Si se conservara solo una fila de cada grupo se excluirían **$75,036.45**; esto es únicamente un escenario de diagnóstico, **no un ajuste autorizado ni una confirmación de sobreconteo**. Hay recurrencias previas en la fuente y no existe ID de factura/línea para distinguir cargos legítimos de duplicaciones. El CSV `datarevenue-repeticiones-2026-10-23.csv` enumera las filas de cada grupo y su presencia en el corte anterior. Estafeta destaca en la variación de $56,156 porque sus dos filas pasan a formar parte de la facturación; no es el único grupo repetido del origen.

## Cambios integrados

- Detalle de proyectos: módulos de Azure (resumen, agrupaciones, filtros, tabla editable y carga), RAID (consulta y alta), IA (fuentes, historial, Drive y acciones) y comunicados (extensión, suspensión, reanudación y cierre).
- API v1 para esas vistas y acciones, manteniendo servicios anteriores, capacidades, alcance y CSRF. La integración no envía correos ni crea registros externos durante la instalación.
- Avisos de datos faltantes y ficha alternativa desde MPB/Histórico para proyectos ausentes de Proyectos.
- Glosario de columnas de la comparativa de márgenes, presentación de campos por validar y ajustes de estilos y tarjeta EVA-4.
- Pruebas backend, modelos JavaScript y navegador del ZIP.

## Adaptaciones y conservación

- Se conserva el formateador decimal validado y su versión en importmap; el ZIP traía una variante menos estricta y eliminaba la versión de caché.
- Se conservan `resolve_full`, `full_span` y el uso explícito del rango completo en RPC. No se aplica el cambio del ZIP que ampliaba por defecto todas las consultas MPB. Se añade únicamente la alternativa MPB cuando falta el inicio histórico; con historial válido se conserva su rango.
- Servicio y Cuenta siguen dentro del encabezado de Operativa.
- No se sustituyen .env, key.json, configuraciones, dependencias, migraciones ni datos por los del ZIP. SQLite se respalda antes de editar fuentes.
- El detalle grande sigue parcialmente migrado; no se retiran el shim ni las pestañas anteriores aún necesarias.

## Verificación

- Backend (portal, core, accesos, AER, Clockify, ejecutivo y Gmail): **1,686 aprobadas, 1 omitida**.
- Rangos de fechas tras la adaptación: **22 aprobadas**, incluidas las tres pruebas nuevas de fallback y conservación del histórico.
- Módulos frontend (`*.test.mjs`): **137 aprobadas**.
- Navegador Chrome: **273 aprobadas**. Incluye las nuevas vistas de IA, Azure, Cliente/Acciones, RAID, comunicados y avisos de datos, más Business Overview, Operativa y márgenes. Se ejecutaron los casos de comparación y anchos de móvil/escritorio definidos en esas pruebas. Se inspeccionó además una captura móvil de Azure a 390 px.
- Suite JavaScript completa: conserva los **tres fallos previos** documentados en AGENTS.md: `cost_sprint_details.test.cjs`, `executive_report.test.cjs` y `financial.test.cjs`. No se borraron ni se modificaron para ocultar el resultado.
- Django `check`: sin problemas. Ruff: análisis aprobado; **597 archivos** con formato correcto.
- Servidor reiniciado en **http://127.0.0.1:8003/**. Respuestas 200 en Business Overview, Operativa, Comercial, módulo de detalle y API ejecutiva. La API devuelve `invoiced: "2006482.71"`.
- SHA-256 de `.env`, `key.json`, `db.sqlite3`, dependencias y `pyproject.toml` idéntico al respaldo previo.

No hay conflictos de integración pendientes. Queda pendiente validar las repeticiones de la fuente con Finanzas y actualizar las tres pruebas heredadas en el trabajo de limpieza del frontend. Las pestañas aún anteriores del detalle grande y los accesos Genesis mantienen el estado parcial documentado; esta integración no los declara terminados.
