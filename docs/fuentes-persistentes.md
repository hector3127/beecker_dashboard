# Lecturas persistentes y caché de resultados

Bloque sobre `f3b0411`, 27–28/10/2026. No cambia frontend, fórmulas,
agrupación de proyectos, permisos ni CSP.

## Qué provocaba las esperas

- Las horas ya estaban en SQLite, pero el catálogo de proyectos de Clockify
  seguía dependiendo de la API y de una caché con vencimiento.
- El panel Azure de IXB/SaaS/RaaS usaba DailyAzureClient directamente y
  evitaba el almacén del gateway. El RAID volvía a descargar las relaciones.
- Finanzas, Operativa, DM y GSE podían conservar cálculos en caché después
  de sincronizar la base. Vaciar toda la caché tampoco era una solución:
  eliminaba configuración útil y no impedía que un cálculo anterior terminara
  tarde y publicara resultados viejos.

## Persistencia

Migración aditiva `datastore.0007_source_read_models`:

- `ClockifyCatalog` identifica el workspace y su última publicación completa.
- `ClockifyProjectRecord` pertenece al catálogo. Clave única catálogo/ID externo.
- `ClockifyTaskRecord` pertenece al proyecto. Clave única proyecto/ID externo.
  Un marcador separa tareas vacías de tareas todavía no sincronizadas.
- `AzurePanelSnapshot` pertenece a un Team Project y registra total y fecha.
  Sus elementos usan `AzureWorkItem.kind=panel`, campos completos y relaciones.
  Se reutilizan los índices proyecto/tipo/posición e ID existentes.
- `DataRevision(pk=1)` es una generación persistente de fuentes, independiente
  de los archivos de caché.

No se convierten nombres internos en IDs externos ni se recalculan horas.
Los payloads JSON conservan la respuesta original de Azure/Clockify; las
identidades, pertenencia, orden y cobertura quedan en columnas y relaciones.
La base existente sigue siendo de una organización de Azure y un workspace
de horas; esto no introduce soporte multiempresa ni cambia el alcance de acceso.

El panel mantiene su límite aprobado de **750** elementos del Team Project,
seleccionados con el mismo ORDER BY ChangedDate y conservando el orden de
cada lote de la API, y su aviso cuando supera ese límite. No se sustituye
por los 1,000 registros de campos limitados del gateway. Las respuestas
incompletas, IDs repetidos y fallos de lotes no se publican como cortes válidos.
La sincronización del gateway conserva el grupo `panel` al reemplazar sus
propios grupos `latest` y `raid`.

La navegación usa primero la base, incluso con caché vacía. RAID reutiliza las
relaciones locales; un refresco explícito del panel publica la nueva copia
completa. Las escrituras RAID invalidan persistentemente el proyecto afectado,
además de su invalidación de caché habitual. También se incluyen
`Clockify_Vinculos` y `WorkItems_Avance` en las hojas persistidas, si existen.
La validez del RAID almacenado ya no depende del contador volátil de caché:
vaciarlo o perderlo no obliga a consultar de nuevo los datos válidos de la base.
Se comprueban ambas vías de alta (Daily e IXS), conservando los demás paneles.

## Coherencia de caché

Cada publicación de hojas, mes de Clockify, proyecto Azure o catálogo
incrementa la generación **en la misma transacción** que sus datos. Un rollback
no cambia esa generación. El middleware fija la generación una vez por
petición; el pool transmite el contexto a sus hilos. Los cálculos que terminen
después de otra sincronización escriben bajo la generación anterior y no
contaminan las siguientes peticiones.

`core.data_cache.make_key` aplica el namespace solo a prefijos de resultados;
conserva claves de sesiones, configuración, candados y estado del refresco.
Las consultas explícitas de fuentes tienen un namespace separado del modo
almacenado. No se cambia la duración de las cachés ni se borra todo al
sincronizar. `warm_cache --refresh`, con almacenes activos, invalida resultados
y precalienta bajo la nueva generación sin borrar configuración.

La caché es una optimización: nunca sustituye el catálogo ni el corte persistente
completo por una respuesta antigua de archivos. Los namespaces anteriores se
eliminan por las políticas de expiración/límite existentes, no por borrados
masivos durante las peticiones.

## Operación

Después de actualizar código en otra instalación:

```powershell
.venv\Scripts\python.exe manage.py migrate
.venv\Scripts\python.exe manage.py sync_read_sources
.venv\Scripts\python.exe manage.py check_datastore --lecturas
```

Requiere la copia previa de Azure (`sync_datastore --pasos azure`) y las
banderas `CLOCKIFY_STORE_ENABLED`, `AZURE_STORE_ENABLED`,
`SHEETS_STORE_ENABLED`. No se modificó `.env`.

- `sync_read_sources --fuente azure --proyecto AMK.004`: actualiza un Team Project.
- `sync_read_sources --fuente clockify`: catálogo de proyectos.
- `sync_read_sources --fuente clockify --tasks`: incluye todas las tareas;
  puede requerir una petición por proyecto. Sin esta opción las tareas necesarias
  para recuperar nombres de CR se guardan al consultarlas por primera vez.
  Cada actualización del catálogo invalida su marcador de tareas para que no
  se consideren vigentes indefinidamente.
- `sync_datastore` añade el paso `lecturas` antes de `catalogos`; el orden
  completo es hojas, Azure, Clockify, lecturas y catálogos internos.
- La definición del trabajo horario en scripts incluye `lecturas`; el diario
  mantiene su sincronización de horas. La revisión añade `--lecturas`, que
  detecta catálogos vencidos y proyectos sin panel completo.
- Azure descarga con un máximo de cuatro sesiones independientes; publica
  desde el hilo principal. Un proyecto fallido conserva su copia anterior y
  el comando termina con error tras procesar los demás.

Se actualizan las definiciones de Windows/pipeline/run_job, pero **no se han
instalado tareas programadas ni desplegado el pipeline**. Si una tarea existente
guarda los argumentos anteriores, debe actualizarse con el script habitual.
Un `--pasos` explícito ejecuta solamente esos pasos; para incluir paneles usar
`hojas,azure,lecturas,catalogos` o el comando específico anterior.

Los flujos sin copia completa conservan el fallback anterior a las fuentes;
no se impone todavía un modo offline global. Metadatos de formularios, consultas
Daily distintas del panel IXS, actualizaciones explícitas y escrituras siguen
pudiendo necesitar las APIs. No afirmar que todo el sistema funciona offline.

## Evidencia local y datos de origen

Antes de migrar se creó una copia consistente con SQLite Backup API:
`tmp/backups/before-source-models-20261027-214410.sqlite3`; `quick_check=ok`.
No se versiona el respaldo ni la base.

La carga real guardó **943 proyectos Clockify**, **111 paneles Azure** y
**38,008 elementos de panel**. Se actualizaron además el resumen del gateway
(111 proyectos), octubre de Clockify (11,694 registros del mes) y catálogos
internos. La base quedó con 534,569 registros de horas, sin cambiar su cálculo.

Con todas las peticiones HTTP externas bloqueadas:

- Panel `AMK.004_CR`: 105 elementos, 0.087 s en el servicio.
- API real `/api/v1/screens/proyectos/AMK.004_CR/azure/`: HTTP 200, CSP activa,
  mismos 105 elementos, 0.573 s incluyendo inicialización del cliente Django.
- Horas `AER.CCO.008`, 01/05–22/10/2026: 1,487 registros, 0.131 s en el servicio.

Son mediciones puntuales locales, no una comparación controlada contra el
tiempo anterior ni una medición completa de navegador.

**Incidencia real pendiente de la hoja:** la nueva lectura de
`Historico_Proyectos` trajo `#REF! (Array result was not expanded because it
would overwrite data in T141.)` en el encabezado 11, donde antes figuraba
Delivery Manager. El catálogo advertía que omitía esa columna y Client.
Se recuperó únicamente esa hoja desde el respaldo, con su timestamp original
del **21/10/2026 14:32 UTC**, y se reconstruyeron los catálogos internos.
No se editó Google Sheets ni se fingió una sincronización reciente.

`save_snapshot` ahora rechaza errores de fórmula en encabezados. Si una hoja
de una sincronización está corrupta se revierte la publicación de todo el lote;
se conserva el último corte válido. `check_datastore --lecturas` sigue marcando
**hojas vencido** por ese histórico hasta corregir T141 en origen y volver a
sincronizar. Los demás almacenes quedaron recientes.

Las pruebas específicas cubren catálogos vacíos/aislamiento de workspace,
ausencia de HTTP, mapeo equivalente, refresco persistente, lotes incompletos,
orden/límite del panel, rollback, cálculos tardíos, configuración de caché,
API real con CSP y encabezados corruptos. La evidencia de regresión del bloque
se registra también en el plan de migración.

Validación: **2,235 servidor** (core, portal, access, datastore, Clockify,
Azure DevOps, Daily y los dos archivos de caché de la raíz) y **476 Node**.
Tras el último ajuste que conserva el orden de los lotes originales se
repitieron **41 pruebas dirigidas** de almacenes con éxito. Ruff, formato,
mypy de pages/los comandos nuevos de lectura y warm_cache, `manage.py check`
y `makemigrations --check --dry-run` aprobados. API de producción comprobada
con CSP y HTTP externo bloqueado, además de los servicios reales mencionados.
No es una corrida completa de e2e ni una comparación visual nueva.

Sintaxis Bash/PowerShell y DryRun de las cuatro tareas comprobados; no se
instalan tareas. El YAML solo cambia argumentos de comandos: no se desplegó
ni se ejecutó su pipeline (PyYAML no está instalado en este entorno).
Las advertencias de servidor sobre `staticfiles/` ausente pertenecen a la
preparación local de pruebas; no hubo fallos de esos casos.
