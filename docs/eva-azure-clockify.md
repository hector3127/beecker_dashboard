# Migración de EVA 1 a Azure y Clockify

## Corrección de consulta de cortes (base 91f48ed)

El usuario reporta que permanece «Consultando estado de extracción…» y no
queda claro cómo consultar una fecha. En el servidor real local se comprobó
API ready, estáticos 200 y Chrome limpio sin errores; no se atribuye un fallo
concreto al navegador del usuario sin evidencia. La página ahora entrega el
estado inicial y las incidencias desde Django, sin esperar JavaScript, y
versiona los módulos de entrada/estado para renovar archivos almacenados.

El formulario GET de fecha/DM/servicio está arriba: funciona sin JavaScript,
durante una extracción y aunque falle la API de estado. Su contrato es
`/operativa/eva-1/?corte=AAAA-MM-DD&manager=...&service=...`. Lee únicamente
un corte publicado de esa fecha; no inicia una extracción ni interpreta la
fecha como Finish de los proyectos. Los enlaces muestran los últimos 60
cortes guardados y conservan filtros. Una fecha pasada no disponible tiene
un aviso específico; Actualizar fuentes crea el corte de hoy.

Las incidencias de una extracción publicada se presentan como aviso de datos
parciales, separado del error de disponibilidad. Se retiró la frase incorrecta
«Las cifras reales aparecerán cuando la conexión responda». La consulta del
estado tiene un límite de diez segundos; el formulario permanece disponible.

Validación: 59 servidor dirigidas (native/cut/retired/kpi_eva), 478 Node y
siete Chrome con rutas reales/CSP. Incluyen JavaScript desactivado, corte
anterior con filtros mientras hay extracción en curso y API de estado 503.
La página real del puerto 8000 reporta la extracción lista, input de fecha
presente, sin errores JS ni descargas fallidas. No se cambiaron cálculos,
reglas de selección, permisos ni datos. No se hizo una nueva extracción.

## Estado vigente: fuente nativa activa (28/10/2026)

Sobre 394562c, el usuario autoriza completar la conexión y medir extracción.
La ruta `/operativa/eva-1/`, su listado de cerrados y los cortes mensuales de
KPIs ya leen cortes locales observados de Azure/Clockify. No consultan
Proyectos ni Histórico_Proyectos. Otros EVA y consumidores compartidos de
load_eva2 mantienen sus contratos y fuentes; no es una migración global del
resto de Operativa, Business Overview, costos o fichas de proyecto.

### Extracción y persistencia

- `sync_eva_native` obtiene el catálogo Azure paginado con sus Summaries.
  Descarga todos los IDs devueltos por WIQL en lotes, sin el tope de 1000
  del lector anterior, y valida la integridad de cada lote. Cuatro conexiones
  concurrentes como máximo por fase. No envía escrituras a los proveedores.
- Una familia sin servicio confirmado queda en diagnóstico. Conserva su
  Summary y omite descargar sus work items/horas; no se presume que sea IXB.
- Identidades de bloque separadas; CR2/S1 se vincula a CR2 solo si esa raíz
  existe en Azure. CR1 a CR exige coincidencia única de ambas fechas.
  La identidad de navegación usa la raíz resuelta, mientras summary_scope
  conserva el encabezado original. No se aplica fuzzy matching a proyectos.
- Estado de cierre confirmado por Summary o Epic General del bloque.
  Finish vencido no cierra un proyecto. Suspendido se conserva cuando está
  explícito. Un estado no verificable queda fuera del TP confirmado con aviso
  de total parcial; no se inventa su etapa o su cierre.
- Burn: registros facturables únicos, en fecha local Start–min(Finish,corte),
  con tarea/tags de nomenclatura exacta. Bloques cerrados que se traslapan
  impiden atribuir sus horas sin etiqueta a otro bloque abierto. La fecha
  o asignación ambigua queda pendiente, igual que un rango invertido.
- Horas históricas desde meses completos de la base Clockify; los meses
  faltantes y el actual se consultan por API. Quedan registrados el sello
  de esa base, meses reutilizados y solicitudes de reportes. No se presenta
  esa reutilización como una descarga HTTP nueva.
- Reglas financieras autorizadas activas: ETC = Budget−Burn; Desv. Hrs =
  min(ETC,0); Advance = Burn/Budget×100. Budget cero deja Advance pendiente.
  Se mantienen conteos General/etapas y alertas según fechas de iteración.
- Migración aditiva 0008: EvaExtraction → EvaAzureSource → EvaScopeSnapshot,
  con claves foráneas y unicidad por proveedor/bloque. El payload original
  se conserva una vez por Team Project/corte, separado de sus proyecciones.
  Solo se publica la extracción con transportes completos. Un fallo conserva
  el corte anterior. Una extracción parcial `--project` no sustituye el
  inventario completo. La generación se cambia en la misma transacción.
- Lecturas de EVA sin caché volátil ni fuentes externas. El selector usa
  el último corte publicado observado en la fecha pedida; no toma estados
  actuales para rellenar una fecha pasada. El inicio de corrida decide el
  orden de publicación visible, para que una corrida vieja tardía no gane.
- Los cerrados se conservan como evidencia. Sus horas quedan pendientes si
  no fueron necesarias para la extracción activa; el plegable lo explica.

La migración 0008 se aplicó localmente después de un respaldo SQLite con la
API backup en `tmp/backups/before-eva-native-20261028.sqlite3`. PostgreSQL
sigue diferido hasta Genesis. No se modificaron credenciales ni fuentes.

### Interfaz y operación

EVA incluye «Actualizar fuentes Azure / Clockify», sello de fuente, tiempos
y un desplegable de incidencias. POST con CSRF y permiso view_operations de
portafolio completo inicia una extracción en segundo plano; GET de estado
solo lee la base. API: `/api/v1/screens/eva1/extraccion/`. Hay coalescencia por
proceso y candado persistente entre procesos. Reintento después de fallo;
éxito recarga el corte conservando los filtros de la URL. No se relaja CSP.

KPIs mensuales mantienen cortes lunes–jueves y las fórmulas T/C. Los meses
sin observación tienen celdas/totales pendientes, no TP=0 inventado; no
entran como cero al promedio trimestral. El histórico nuevo empieza con las
observaciones reales guardadas desde el 28/10. No se importaron ni
reconstruyeron meses anteriores desde Sheets o desde el estado de hoy.

El paso `eva` se incorpora a sync_datastore y las definiciones de horario,
diario y pipeline. `--sin-azure` también lo omite. Se validaron Bash y DryRun
Windows con ProjectDir explícito; no se instalaron tareas ni se desplegó el
pipeline. Para ejecutar de forma independiente, sin Sheets:

```powershell
.venv/Scripts/python.exe manage.py sync_eva_native --output tmp/eva-performance.json
.venv/Scripts/python.exe manage.py sync_datastore --pasos eva
```

### Mediciones reales y límites

En esta máquina, conexión y datos del 28/10; no es una prueba de capacidad de
producción ni una comparación controlada de latencia de proveedores:

| Fase | Última extracción optimizada |
| --- | ---: |
| Catálogo Azure | 0.346 s |
| Summary/work items/iteraciones Azure | 36.547 s |
| Clockify, catálogo/horas | 29.745 s |
| Persistencia/publicación | 1.410 s |
| Total | 68.052 s |

356 proyectos con identificador de negocio revisados, 453 bloques. Se
consultaron work items de 153 proyectos y se conservaron 201 proyectos de
Summary sin clasificación en diagnóstico; dos no pertenecían a la familia.
30 solicitudes de reportes Clockify y 229 meses/proyecto leídos de su base.
Corridas anteriores: 102.531, 118.988 y 130.750 s; las dos últimas aún
consultaban registros de familias sin confirmar. Los tiempos de red varían.
Artefactos locales: tmp/eva-native-performance-optimized.json y anteriores.

Lectura del corte local y generación de HTML, cinco repeticiones, con
requests y construcción del repositorio Sheets bloqueados: mediana 0.0196 s
de lectura y 0.1433 s de render servidor. No incluye navegador, red ni
descarga de assets. Artefacto tmp/eva-native-read-performance.json.

El corte muestra 68 bloques abiertos con servicio/estado confirmados. Hay
234 sin servicio y 29 sin estado confirmado fuera de ese TP, con aviso
explícito de total parcial, y 271 incidencias de origen. No equivale a
afirmar que esos 263 bloques sean proyectos abiertos de EVA. Completar
Summary/iteraciones en Azure permite clasificarlos en la próxima extracción.
La fecha 29/10/025 sigue inválida; no se corrige por suposición. La alerta
de #REF! de Sheets sigue vigente para las otras pantallas que lo usan.

### Validación

- Regresión servidor: 2183 aprobadas en portal/core/access/datastore/
  clockify/capacidad/azure_devops (103.43 s). Tras los últimos ajustes,
  71 dirigidas de extracción, parser y programación aprobadas, con
  solapamiento; no se suman como una suite distinta completa.
- Node: 478 aprobadas. Chrome: cinco casos con config.urls real y CSP:
  390/900/1450 px, CSV, cerrados, CSRF, recarga tras éxito y reintento tras
  fallo conservando tabla. Las esperas de navegador no usan unsafe-eval.
- Capturas en tmp/eva-native/eva-{ancho}.png. Revisadas móvil y escritorio;
  min-width de tarjetas y encabezados responsivos conservan la presentación
  vigente. No se regeneraron referencias anteriores. Skill ui-ux-pro-max.
- Ruff/check/formato de archivos propios, mypy pages.py, manage.py check y
  makemigrations --check aprobados. Avisos staticfiles de preparación de
  pruebas sin collectstatic. Sin push; fase 11 de migración sigue abierta.

## Histórico: primer bloque de lector (28/10/2026)

Base bda55fe. El usuario autoriza iniciar la sustitución de Sheets y del
Histórico por Azure/Clockify y consultar, sin modificar, la referencia
`C:/qa_automation_platform/apps/msp_qa/`. Se revisaron block_splitter,
description_parser y azure_iterations. No se copian credenciales ni se
añaden dependencias entre repositorios.

La tabla de IXB/RaaS/SaaS referida como EVA 1 corresponde internamente a
eva2/ixb_summary y eva_cut. El módulo interno eva1 corresponde a AER/T&M.
No cambiar el módulo equivocado por la nomenclatura de las pantallas.

### Implementado

- Lectura GET del Summary/description con el cliente Azure existente.
  Contrato oficial: [Projects Get](https://learn.microsoft.com/en-us/rest/api/azure/devops/core/projects/get?view=azure-devops-rest-7.1).
- Diccionario explícito de etiquetas en español, inglés y portugués para
  DM, ID, servicio, nombre, cliente, inicio, fin, presupuesto y estado.
  Normaliza acentos y separadores. Reconoce metadatos de roles/duración
  por separado y reporta etiquetas desconocidas sin adivinar equivalencias.
- Texto y HTML, incluidos pares de celdas de tablas; sin ejecutar HTML.
- Bloques S#, CR, CR#, y compuestos CR#_S#. Reconoce el caso real
  `CHANGE REQUEST 2 / SPRNT 1`. CR y CR1 permanecen distintos.
- Horas con sufijos de bloque quedan en el bloque correspondiente.
  No se heredan presupuesto, fechas, ID ni estado a bloques hijos.
  Solo nombre, cliente, servicio y DM explícitos del preámbulo son comunes.
- Encabezados duplicados, campos contradictorios, fechas inválidas y
  presupuestos ambiguos quedan como incidencias. No gana el último valor.
- Función financiera aislada con las reglas recién autorizadas por el
  usuario: ETC = Budget - Burn; desviación = min(ETC, 0); avance =
  Burn/Budget × 100. Budget cero deja avance pendiente; Burn ausente no
  equivale a cero. No modifica todavía los cálculos de la pantalla activa.
- Comando audit_eva_azure: solo lee proyectos seleccionados, escribe un
  informe local y no publica cortes. Puede reproducir muestras sin red.

```powershell
.venv/Scripts/python.exe manage.py audit_eva_azure --project AMK.012 --project MCC.023 --output tmp/eva-azure-audit.json
# Reproducción de una muestra local {"PROYECTO": "descripción"}:
.venv/Scripts/python.exe manage.py audit_eva_azure --project AMK.012 --input tmp/azure-summary-samples.json --output tmp/eva-azure-audit.json
```

Los informes pueden contener nombres de personas; son artefactos locales,
no se comitean. `ready` significa interpretación estructural completa del
Summary, no aprobación de la relación Clockify ni integridad histórica.

### Evidencia real y pruebas

Se consultaron AMK.012, MCC.023 y NSC.B.003 por GET con la conexión actual:
8 bloques, 7 estructuralmente completos, ningún proyecto fallido.
AMK.012 tiene CR2/S1, CR1/S1 y S1: se mantienen separados. CR1/S1 trae
`29/10/025`; se reporta invalid_start, no se convierte a 2025 por suposición.
Los valores `90 hrs.` y `412 a utilizar` se reconocen como horas.
No se deduce que AMK.012_CR del portal corresponde a CR1/S1 o CR2/S1.
Muestras e informe locales en tmp/azure-summary-samples.json y
tmp/eva-azure-audit.json, obtenidos el 28/10/2026.

`pytest tests/azure_devops tests/datastore/test_azure_store.py -q --no-cov
--tb=short`: 75 aprobadas, incluidas 26 nuevas de bloques, conflictos,
HTML, fechas, presupuestos, fórmulas y comando offline sin conexión Azure.
Ruff/check y format de los cinco archivos Python del bloque aprobados;
manage.py check sin incidencias. No se requieren pruebas visuales: no hay
cambios de frontend ni de rutas activas. No se afirma regresión completa.

### Continuación necesaria antes de retirar Sheets

1. Ampliar la auditoría al inventario autorizado completo. El comando pide
   proyectos explícitos; no implica que el catálogo actual sea exhaustivo.
2. Persistir versiones del Summary y el origen/fecha de cada campo en la
   base actual; no llevar peticiones por proyecto al render de EVA.
3. Relación explícita de cada bloque con proyecto/tarea/tags de Clockify.
   Verificar CR vs CR1 y los compuestos con evidencia, sin unir por parecido.
4. Burn facturable en Start–Finish, limitado al corte, con cobertura de
   sincronización comprobada y asignación exclusiva por nomenclatura.
   No sumar dos veces registros de proyectos/bloques que comparten catálogo.
5. Estado y conteos por iteración/bloque, incluyendo suspendidos y
   excluyendo cerrados/completados. Riesgos activos al corte: guardar o
   consultar revisiones; el estado actual no reconstruye el estado pasado.
6. Cortes históricos locales y KPI mensual (último lunes–jueves del mes),
   permisos, filtros y contratos de API existentes; comparar con evidencia
   antes de activar la nueva fuente. No inventar históricos anteriores.

La fuente activa de EVA sigue igual al cierre de este primer bloque.
No se ha aplicado migración de base, modificado Sheets/Azure/Clockify ni
silenciado la incidencia #REF! de origen. PostgreSQL espera Genesis y las
evaluaciones esperan la plantilla oficial. Sin push.
