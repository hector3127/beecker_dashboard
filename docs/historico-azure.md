# Histórico Azure para el inventario EVA

El usuario autoriza descargar y almacenar los estados pasados de todos los
proyectos accesibles por el PAT. Se usa Reporting Work Item Revisions de
Azure, que permite recorrer el historial completo por cursor e incluir
elementos eliminados. No se generan estados pasados desde los estados actuales.

Fuentes oficiales:
- https://learn.microsoft.com/en-us/rest/api/azure/devops/wit/reporting-work-item-revisions/read-reporting-revisions-get?view=azure-devops-rest-7.1
- https://learn.microsoft.com/en-us/rest/api/azure/devops/boards/queries/wiql-syntax?view=azure-devops

## Operación

`.venv/Scripts/python.exe -u manage.py sync_azure_history`

La primera ejecución recorre todas las revisiones retenidas y visibles al PAT.
Las siguientes continúan desde el cursor; una interrupción conserva los lotes
validados. Candado único y reintentos limitados con espera para 429/5xx y
errores de conexión. 401/403 no se reintentan. Se conserva el error del feed.
La descarga no borra datos de origen ni cambia permisos ni configuración.

La organización se consulta como un solo feed para conservar los cambios de
proyecto de un work item: el último estado global decide a qué proyecto
pertenecía, evitando contabilizarlo dos veces tras un movimiento.

## Persistencia y cortes

Migración aditiva 0009: AzureHistoryFeed, AzureWorkItemRevision y
AzureHistoricalCut. El feed se aísla por hash de organización/PAT; no almacena
el secreto. Revisiones únicas por feed/ID/revisión, proyecto y fecha indexados.
El cursor y cada lote se guardan juntos. Cobertura completa solo se publica
al recibir isLastBatch; un feed parcial no genera ceros históricos.

Para el corte se elige la última revisión anterior a la medianoche del día
siguiente en America/Mexico_City, excluyendo eliminados y elementos de otros
proyectos. Conteos y riesgos se proyectan con las identidades y reglas EVA
existentes y se materializan por fuente/corte. La página no llama a Azure.
El cálculo se invalida cuando avanza la cobertura del feed. Hoy conserva la
observación actual; fechas futuras sin cobertura siguen sin datos inventados.

Summary, asignación del DM y fechas de iteraciones siguen siendo la información
guardada del inventario actual. Este bloque reconstruye work items/riesgos,
no promete recuperar versiones pasadas de Summary o fechas de programación.
Solo se puede recuperar lo que Azure conserva y el PAT permite consultar.
Los cortes publicados del EVA nativo y sus KPI no cambian.

Respaldo local previo a migración:
`tmp/backups/before-azure-history-20261028.sqlite3`. Migración aplicada en
SQLite; PostgreSQL continúa diferido hasta Genesis.

## Evidencia real, 28/10/2026

781,628 revisiones únicas de 131,921 work items y 414 nombres históricos de
proyecto, desde 2021. Primer intento guardó 22,000 revisiones antes de un 503.
Reanudación: 760 lotes/759,628 revisiones en 571.222 s. Actualización posterior:
cero revisiones nuevas en 0.204 s, sin repetir la descarga completa.

Al 30/09/2026, once bloques visibles tienen métricas históricas. Lectura local
medida una vez: 1.184 s al materializar y 0.512 s usando las proyecciones
guardadas. Auditoría AMK.004 contra WIQL ASOF y workitemsbatch asOf: 303 IDs
iguales y cero diferencias en estado, tipo, título e iteración. Artefactos
locales: tmp/azure-history-asof-audit.json y tmp/compare_azure_history.py.

Chrome local confirma septiembre con cifras y sin errores JS/spinner residual.
Seis pruebas Chrome con rutas reales/CSP aprobadas, incluyendo histórico,
carga, valores persistidos y tres tamaños. Tests servidor cubren revisiones,
eliminación, cambio de proyecto, frontera de día México, reanudación,
reintentos, aislamiento por token y rechazo de lotes inválidos.
Validación final servidor: 226 pruebas (datastore, Azure, histórico y servicios
del inventario/EVA). Ruff, mypy, manage.py check y ausencia de migraciones
pendientes aprobados. Sin cambio de permisos, PostgreSQL, programación
instalada ni push.
