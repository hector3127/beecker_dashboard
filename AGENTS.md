# AGENTS.md — Migración del frontend de Beecker

Guía para continuar la migración con cualquier agente (Codex, Claude Code…). Lee esto y `docs/plan-migracion-frontend.md` antes de tocar nada.

## Objetivo

**Tarjetas EVA, criterio posterior confirmado 28/10:** T=desviación <= 0 / TP;
C=avance > 100% / TP, sobre todos los proyectos de la tabla filtrada. C expresa
sobrecosto, no cumplimiento. Pendientes permanecen en el denominador. Este
cambio es solo de tarjetas EVA; KPIs mensuales DM conservan su definición.

**EVA, actualización 28/10:** retirado el extractor previo al inventario Summary,
sus rutas/panel y datos exclusivos (0010/0011 con respaldo). EVA y KPIs usan
el inventario nuevo. Suspendido solo con evidencia explícita Azure: RSP activo;
RCP requiere ProjectSituation Suspended. Nunca inferirlo de huecos del calendario.
T/C son porcentajes sobre todos los proyectos visibles. Ver
`docs/retirada-eva-anterior.md`; diez Chrome y 21 servidor finales aprobados.
Sin push. Este bloque sustituye las instrucciones anteriores del extractor EVA.

Pasar cada pantalla del portal a `frontend/` con HTML, CSS y JS separados. Django sigue como servidor.

Reglas que no se negocian:

1. **Conservar el diseño actual aprobado por el usuario.** No modificar estilos, estructura visual ni componentes para igualarlos al old. Comparar apariencia con la línea base actual; conservar cifras, filtros, exportaciones, permisos y regreso.
2. **No cambiar cálculos ni reglas de negocio.** Si algo parece mal, repórtalo; no lo "arregles" para que coincidan reportes.
3. **No activar `ACCESS_ENFORCED` en producción** sin accesos configurados.
4. **Horas por mes** (`cuenta/<slug>/horas/`) se conserva tal cual: filtros de fechas y proyectos, CSV, permisos y regreso a la cuenta.
5. Commits pequeños y cuidados **directo en `main`** (único desarrollador, sin ramas). **No hagas push** salvo que el usuario lo pida expresamente.
6. Nunca subas `.env`, `key.json` ni credenciales. No toques cambios sin commitear que no sean tuyos.
7. Solo marca una pantalla como terminada cuando su ruta activa usa la plantilla de `frontend/`, conserva su funcionamiento y tiene pruebas y comparación visual con el diseño actual aprobado.
8. Actualiza `docs/plan-migracion-frontend.md` con evidencia real en cada bloque.
9. Lecturas de frontend con `apiGet` o el catálogo compartido de logos; no
   añadir fetch directo para leer datos. Conservar la excepción documentada
   de escritura multipart de logos. No revertir 0de6c7d, 3410e89, 47d0364
   ni el comportamiento de Capacidad diaria de 834bbfa.

## Estado vigente (27/10/2026)

**EVA 1 integrado con inventario, 28/10:** por instrucción del usuario,
views.eva1 usa eva_inventory_view/inventory_rows y pivotes dm_totals con el
rango inclusivo de iteraciones, horas locales e histórico Azure. Apariencia
EVA conservada; ver docs/eva-inventario-activo.md. Actualizar fuentes refresca
Summary/Clockify e histórico incremental. KPI mensual/otros EVA no cambian.
No restaurar para esta ruta el filtrado del antiguo snapshot nativo.

**Histórico inventario Summary, 28/10:** descarga autorizada de revisiones
Azure, cursor incremental y migración 0009 aditiva con respaldo SQLite.
781,628 revisiones/131,921 WIs. Corte local materializado por fuente/fecha;
septiembre completo, auditoría 303 WIs ASOF sin diferencias. Ver
docs/historico-azure.md. Sustituye Sin histórico solo con cobertura comprobada;
no inventa Summary/DM/fechas antiguos ni modifica EVA/KPI nativos. Comando
sync_azure_history incremental, sin tareas instaladas ni push.

**Corrección del filtro EVA, base 91f48ed:** formulario GET de fecha/DM/
servicio operativo sin JS o con estado 503; estado inicial renderizado en
Django, módulos versionados y avisos parciales separados de conexión.
Cortes disponibles visibles; no esperar extracción para consultar. 59
servidor dirigidas, 478 Node y siete Chrome/CSP aprobadas, página real
local sin errores. Ver docs/eva-azure-clockify.md. Sin nuevas extracciones,
cambios de datos, cálculos o permisos; fase 11 abierta.

**EVA 1 nativo activo, 28/10, base 394562c:** por autorización del usuario,
la ruta EVA 1, cerrados y KPIs mensuales leen cortes locales de Azure/Clockify,
sin Proyectos/Historico_Proyectos. Migración aditiva 0008 aplicada con respaldo
SQLite; no PostgreSQL. Summary y bloques conservados; cierre por estado
explícito/General, no por Finish. Horas facturables por rango y tarea/tags,
sin duplicación entre sprints/CR. Cortes anteriores sin observación quedan
pendientes; no reconstruirlos con el Azure actual. TP parcial cuando faltan
servicio/estado confirmados. Botón de extracción, CSRF/alcance total,
background/candado, tiempos e incidencias. Última medición: 68.052 s total,
36.547 Azure, 29.745 Clockify, 1.410 persistencia; lectura local 0.0196 s y
render 0.1433 s (medianas de cinco). Ver docs/eva-azure-clockify.md.
2183 servidor, 71 dirigidas posteriores con solapamiento, 478 Node y cinco
Chrome reales/CSP aprobadas. Definiciones de programación incluyen eva;
no se instalaron tareas. Otros EVA/BO/costos conservan fuentes y contratos.
No se oculta #REF! de origen. Sin push; fase 11 abierta.

**Inicio EVA Azure/Clockify (28/10), base bda55fe:** el usuario autoriza
retirar la dependencia de Sheets para EVA y define ETC=Budget-Burn,
Hours Deviation=min(ETC,0), Advance=Burn/Budget*100 y riesgos activos al
corte. Primer bloque solo lector/auditoría, no cambia fuente activa.
Ver docs/eva-azure-clockify.md: 8 bloques reales, 7 completos, fecha
29/10/025 pendiente. No unir AMK.012_CR con CR1/S1 o CR2/S1 sin evidencia.
75 pruebas Azure/almacén pasan. PostgreSQL sigue esperando Genesis.

**Acuerdos de demo, 28/10, base a187954:** filtro de plantilla por corte en
facturabilidad, desglose diario por persona en Capacidad y enlaces del plan
en Planeación. Manual y evidencia en docs/cambios-demo-2026-10-27.md.
El usuario difiere expresamente PostgreSQL hasta Genesis y la importación
de evaluaciones hasta recibir la plantilla oficial. No implementar esos
dos pendientes ni cambiar conexión. 2101 servidor, 38 dirigidas con
solapamiento, 478 Node y 15 Chrome con rutas reales/CSP aprobadas.
Prueba local sintética 64/64 con ocho conexiones; no valida producción.
Sin push; fase 11 abierta. No se oculta el error de origen del Histórico.

**Nuevo bloque de persistencia, base f3b0411.** El usuario pidió reducir
peticiones externas y evitar resultados de caché anteriores a la base.
Ver `docs/fuentes-persistentes.md`: migración aditiva 0007, catálogos Clockify,
panel Azure/relaciones persistidos y generación de caché dentro de la misma
transacción que los datos. No cambiar cálculos ni diseño para esta tarea.
La sincronización incluye el paso `lecturas`; las definiciones de tareas
se actualizan, pero no se han instalado. Conservar el fallback explícitamente
documentado: no afirmar que todos los formularios/Daily funcionan offline.
Incidencia de origen: Histórico devuelve #REF! por T141. Se conservó su copia
válida del respaldo con fecha original; el monitoreo debe seguir avisando
de su antigüedad hasta corregir Sheets. No ocultar ese fallo ni actualizar
artificialmente su timestamp. Validados 2,235 servidor y 476 Node, más 41
dirigidas tras el último ajuste; ver alcance en fuentes-persistentes.
RAID se invalida persistentemente por proyecto tras escritura, sin depender
de un contador volátil de caché. Corrección posterior de CacheKeyWarning:
claves no portables usan SHA-256 de su identidad completa, sin modificar IDs;
170 dirigidas aprobadas. GPO.001_ CR no tiene rango en el histórico local:
no asignarle automáticamente el del proyecto base. No se hizo push.

**Excepción autorizada posteriormente por el usuario: rediseño de Proyectos.**
El usuario pidió renovar todas las pestañas del detalle de proyecto, con
gráficas/tablas responsivas y mejor organización. Esa vista usa ahora el
sistema `delivery-v2` documentado en `docs/diseno-proyectos.md`; no debe
forzarse su apariencia contra el old ni contra referencias previas al
rediseño. Se conservan cálculos, permisos, fuentes, acciones y navegación.
La restricción de conservar el diseño sigue vigente para las otras páginas.
Las referencias nuevas identifican explícitamente el rediseño solicitado;
no implican una aprobación visual posterior que el usuario aún no ha dado.
La segunda revisión pide usar Business Overview como referencia visual y
revisar cada pestaña en distintos tamaños. Mantener los ajustes de escala,
tablas y el gráfico responsivo de evaluaciones; no cambiar sus valores.

**Criterio vigente por instrucción del usuario:** conservar el diseño actual
aprobado, sin cambios en HTML/CSS/JS de la aplicación para igualarlo al old.
Las referencias visuales se capturan del diseño actual; la base de cada
bloque queda registrada en sus archivos y evidencia.
Las expectativas originales de Node validan funcionamiento/cálculos, no
imponen el aspecto antiguo. El piloto AER se actualiza a este criterio;
los demás tests visuales anteriores requieren clasificación antes de seguir.
No regenerar referencias automáticamente ante un fallo: investigar primero.

**Fase 10 completada; fase 11 abierta.** Este apartado sustituye los estados
históricos del plan y del traspaso. No reabrir pantallas migradas ni restaurar
presentaciones retiradas. Leer primero el bloque vigente de ambos documentos.

### Git y piloto de congelación

- Último bloque sobre `1478793`: Recursos AER usa 15 referencias del diseño
  actual (9 vistas y 6 formularios). 18 Chrome con CSP/rutas de producción
  y 473 Node pasan; pruebas CRUD/selección/respuestas tardías conservadas.
  No se modificó apps/ ni frontend/. Quince capturas reproducibles; dos alteraciones
  detectadas (geometría y formulario). Seguir navegador con
  diseño actual; no imponer el old. Ver congelacion-referencias. Sin push.
- Último bloque sobre `3c0f9cc`: piloto navegador de Ejecutivo AER completado.
  Nueve JSON originales (1905 elementos) reproducibles byte por byte. Las 13
  pruebas permanentes pasan con CSP y rutas de producción, sin directorios
  de referencia; no abren vista=anterior. Tres alteraciones de DOM detectadas,
  473 Node pasan. PNG: 6 idénticos y 3 con mínima diferencia de pintado en el
  texto de la dona móvil, diagnosticada sin cambiar app/CSS ni tolerancias.
  Seguir otros bloques de navegador; no repetir el piloto. Sólo cambia tests/
  documentación; no se repiten servidor ni se hace push. Ver congelacion-referencias.
- Bloque previo sobre `6f69346`: actualización de cortes usa tests del
  controlador/cliente actuales; ningún test Node lee tests/reference.
  Restaurados no-store de cliente/API y parada de sondeo tras fallo, sin
  cambios de diseño, cifras, fórmulas o permisos. 473 Node en UTC/México,
  ocho mutaciones, 23 servidor dirigidas, 29 Chrome y una revalidación de
  producción con CSP pasan (hay solapamiento). Regresión amplia servidor
  aprobada: 1747 casos (portal/core/access). Navegador/congelación general
  siguen pendientes; no borrar originales/generadores aún. Sin push.
- Bloque previo sobre `b33c4f1`: carga, navegación y CSS ya no leen referencias
  anteriores. Diez pruebas conservadas; 472 Node y 10 dirigidas pasan en
  UTC/México. Seis mutaciones en copias detectadas y JSON reproducible.
  Carga/navegación ejecutan módulos actuales; CSS se contrasta con SHA-256
  original (solo CRLF/LF normalizados). Queda una lectura auxiliar Node:
  cached_page.test.cjs; auditar el flujo API de cut.js frente al anterior
  antes de reemplazar caché/reintento/aplicación del corte. Navegador pendiente.
  No cambia aplicación ni se repiten servidor/e2e o push. Ver congelacion-referencias.
- Bloque previo sobre `884fb69`: legacy_tools y project_compatibility ya no
  leen el motor original. Diez pruebas conservadas, con controlador/vista/DOM
  y runtime actuales. 472 Node y 10 dirigidas en UTC/México pasan; ocho
  mutaciones en copias detectadas y dos JSON reproducibles. Los 41 tests del
  inventario de proyecto_detalle.js están convertidos. Aún quedan 4 archivos
  con referencias auxiliares Node: cached_page, portal_loading,
  return_navigation y CSS en project_independence; además, navegador.
  No borrar tests/reference ni dar por cerrada fase 11. Sin cambios de
  aplicación, nueva corrida servidor/e2e o push. Ver congelacion-referencias.
- Bloque previo sobre `52fb330`: estado, adaptadores IXB y ambos grupos de
  contextos ya no leen el original. 24 pruebas conservadas; 472 Node y 24
  dirigidas pasan en UTC/México. Doce mutaciones en copias detectadas y
  cuatro JSON reproducibles. Los setters ahora prueban identidad al escribir
  objetos. Quedan 2 archivos Node: legacy_tools y project_compatibility,
  39 convertidos; navegador pendiente. El helper original_state solo se usa
  por generadores temporales, nunca por los tests normales. Sin cambios de
  aplicación ni nueva corrida servidor/e2e o push. Ver congelacion-referencias.
- Bloque previo sobre `611e820`: Ejecutivo genérico, fuentes diferidas,
  paneles AER y puente de carga congelados. 23 pruebas conservadas; 472 Node
  y 23 dirigidas pasan en UTC/México. Diez mutaciones en copias detectadas,
  cuatro JSON reproducibles. El cierre esperado usa la línea de tiempo
  original, nunca el modelo comprobado. Quedan 6 archivos Node dependientes
  del original, 35 congelados. Seguir estado/contextos/adaptadores/compatibilidad.
  No cambia aplicación ni se repiten servidor/e2e; piloto navegador pendiente.
  Ver `docs/congelacion-referencias.md`. Sin push.
- Bloque previo sobre `6336783`: IA, Esfuerzo y soporte IXB, Planeación AER
  congelados desde el original. Cuarenta pruebas conservadas, incluidas seis
  de controladores/estados que siguen activas. 472 Node y 40 dirigidas en
  UTC/México pasan; diez mutaciones en copias detectadas y cuatro JSON
  reproducibles. Quedan 10 archivos Node dependientes del original, 31
  congelados. Seguir modelos genéricos y después contratos/arranque.
  No cambia aplicación ni se repiten servidor/e2e; piloto navegador pendiente.
  Ver `docs/congelacion-referencias.md`. Sin push.
- Bloque previo sobre `98698cd`: Riesgos AER, línea de tiempo general,
  Ejecutivo IXB y Planeación IXB congelados desde el original. Quince pruebas
  conservadas; añadido un caso de vencimientos a mitad/final de semana que
  faltaba. 472 Node y 15 dirigidas en UTC/México pasan; ocho mutaciones en
  copias detectadas. Cuatro JSON reproducibles sin modelos actuales en sus
  generadores. Quedan 14 archivos Node dependientes del original, 27
  congelados. Sin cambios de aplicación ni nueva corrida servidor/e2e o push.
  Ver `docs/congelacion-referencias.md`; piloto navegador pendiente.
- Bloque previo sobre `c1d0308`: resumen Azure IXB congelado (cuatro estados,
  doce campos, cinco pruebas conservadas). 472 Node y cinco dirigidas en
  UTC/México aprobadas; dos mutaciones en copias detectadas y JSON reproducible.
  Clasificadores actuales sin helpers originales en el test. Quedan 18
  archivos Node dependientes del original, 23 congelados. Sin cambios de
  aplicación ni nueva corrida servidor/e2e o push; piloto navegador pendiente.
- Bloque previo sobre `4c7767a`: ixs_resources compara cuatro resultados
  completos y cuatro casos del editor contra JSON original reproducible.
  472 Node pasan; tres mutaciones en copias detectadas. No cambia aplicación,
  diseño, cálculos, CSP ni permisos; sin nueva corrida servidor/e2e o push.
  Quedan 19 archivos Node dependientes del original, 22 congelados en total.
  Ver `docs/congelacion-referencias.md`; piloto de navegador pendiente.
- Base publicada: `a370589`; main ya incluye la actualización documental
  `1c37925` y el piloto integrado en `2e580ec`, con nuevos cambios locales de
  congelación. Comprobar Git al comenzar; no hacer push sin petición expresa.
- Rama local existente `congelar-referencias`: `4103ed6`, un commit sobre main.
  Primer caso: `tests/frontend/aer_executive.test.mjs` compara contra
  `tests/frontend/frozen/aer_executive.json`; el generador está en
  `tests/frontend/frozen/gen/aer_executive.gen.mjs`. **Integrado en main**
  mediante cherry-pick `2e580ec`; la rama local se conserva intacta y no
  figura publicada. No volver a aplicar ese commit ni repetir el piloto.
- El bloque siguiente congela aer_ai_actions_model, aer_planning_filters y
  generic_header: 26 pruebas en los cuatro archivos y 472 Node completas
  aprobadas. Cuatro alteraciones deliberadas en copias temporales fueron
  detectadas. Generadores reproducibles normalizando CRLF/LF, sin cambiar
  valores JSON. Ver `docs/congelacion-referencias.md`.
- Bloque previo sobre `7d59edf`: client_model, project_entry_model,
  ixs_work_items y project_session_model ya no leen el original. Sus 22
  dirigidas y 472 Node completas pasan; cuatro mutaciones en copias se
  detectan. Cuatro JSON originales reproducibles normalizando CRLF/LF.
  Ocho archivos congelados en total; no se modifica código de aplicación.
- Bloque previo sobre `5814968`: raid_create_model, ixs_azure_groups,
  generic_panels y project_clockify_range ya no leen el original. 14 dirigidas
  y 472 Node completas pasan; cinco mutaciones en copias se detectan. Los
  formatos de fechas se comprueban en UTC y America/Mexico_City, restaurando
  TZ. Cuatro JSON reproducibles desde el original; doce archivos congelados
  en total. No cambian aplicación, cálculos, diseño, CSP ni permisos.
- Bloque previo sobre `1f0dbef`: aer_ai_model, aer_effort_model y raid_model
  usan JSON del original. 6 contextos/hechos, 12 resúmenes/estados y auxiliares
  de severidad/cierre. 22 dirigidas pasan en UTC y México; 472 Node completas
  aprobadas. Cuatro mutaciones en copias se detectan; resultados reproducibles
  normalizando CRLF/LF. Quince archivos congelados en total, sin cambiar aplicación.
- Bloque previo sobre `15f619d`: project_shell_model, generic_charts e
  ixs_azure_table usan JSON del original (etapas/estados, geometrías/barras y
  filtros/parsing). 472 Node y 14 dirigidas en UTC/México aprobadas; cuatro
  mutaciones en copias detectadas. JSON reproducibles, sin cambiar aplicación.
  Dieciocho archivos congelados en total; evidencia en congelacion-referencias.
- Bloque previo sobre `81b6d12`: aer_resources_model, actions_model y
  aer_ai_presentation_model ya no leen el original. 472 Node y 41 dirigidas
  en UTC/México aprobadas; cinco mutaciones en copias detectadas. Generadores
  independientes, incluida presentación IA con hechos/contexto originales.
  JSON reproducibles y veintiún archivos congelados, sin cambiar aplicación.

### Aplicación y seguridad

- Todas las páginas activas usan `frontend/`. Se retiraron los directorios
  `apps/portal/templates/portal/` y `apps/portal/static/portal/`.
- La referencia del detalle anterior vive en `tests/reference/`, solo para
  pruebas; `?vista=anterior` no selecciona una página anterior en producción.
  `_modern`, `anterior_disponible` y `ANTERIOR_HASTA` ya no existen.
- `/api/rpc/` ya no se publica en `config.urls`. El shim se movió a
  `tests/reference/static/core/js/gas_shim.js`; solo lo sirven las pruebas.
- **CSP obligatoria por defecto**: `CSP_ENFORCE=True`, nonce por petición y
  dos hashes exactos de estilos de captura, sin unsafe-inline/unsafe-eval.
  Para solo reportar se necesitan **CSP_ENFORCE=0 y CSP_REPORT_ONLY=1** juntos.
  No cambiar esta política como parte de congelar ni activar ACCESS_ENFORCED.
- `tests/conftest.py` activa `reference_site` automáticamente. La suite normal
  puede montar RPC y detalle anterior; verificar también rutas reales
  `config.urls`, sin directorios de referencia y con CSP activa.
- Conservar `views.ejecutiva`, `views.comercial`/`comercial_response`,
  `dm_state`/`dm_rows` y servicios de caché: los usan la API o la precarga.
  **No borrar core/rpc en bloque:** `warm_cache` usa `get_rpc_function` y
  varios módulos usan `register_rpc`. Separar transporte/política de pruebas
  del registro interno antes de decidir su retiro.

### Auditoría independiente sobre main a370589

27/10: **1759 servidor, 472 Node y 61 Chrome con rutas reales/CSP aprobadas**;
además, una prueba de preview de logos aprobada por separado en su preparación
Report-Only. Los 61 casos incluyen las cinco familias de proyecto/pestañas,
Cuenta, Costos, Comercial, PNG y logos. No es una corrida completa de e2e.
Ruff (excluyendo temporales ajenos), mypy de pages.py, `manage.py check` y
`collectstatic --dry-run` aprobados. La primera ejecución del adaptador de
auditoría falló por interpretar un directorio estático con prefijo como Path;
se corrigió solo el adaptador temporal y se repitió satisfactoriamente.

Comandos, límites y hallazgos: `docs/auditoria-fase11-2026-10-27.md`.
No usar los antiguos recuentos «11 HTML/29 estáticos» como estado actual.

### Limpieza y archivos locales

`a370589` retiró 56 maquetas de `design/` y archivó notas sueltas en
`docs/archivo/`, sin modificar la aplicación. Claude reportó limpieza local
de temporales/cachés; esa eliminación no se puede verificar mediante Git.
No borrar `tmp/backups/`, CSV de datos, `.cache`, `graphify-out`, SQLite,
`.env` ni `key.json` como si fueran residuos de la migración.

No tocar ni comitear cambios ajenos en `tools/migracion/inline2css.py`,
`migrate_css.py`, `migrate_page.py`, `shots_tmp/` o `tests/e2e/test_zz_*.py`.
Agregar archivos por nombre. `docs/` contiene decisiones y evidencia; no
eliminar documentos por antigüedad. Retirar solo duplicados sustituidos y
comprobar sus enlaces. El prompt de continuación antiguo se retiró: estas
instrucciones y `docs/estado-traspaso.md` son la entrada vigente.

### Siguiente bloque, en orden

1. Piloto ya integrado: no rehacerlo ni cambiar de rama con cambios ajenos.
   Continuar por modelos Node sencillos y después intermedios/complejos;
   el desarrollo normal sigue directo en main.
2. Guardar la apariencia del diseño actual aprobado como línea base visual.
   Las expectativas originales sirven para funcionamiento/cálculos, no para
   imponer el diseño old. No editar la aplicación durante esta limpieza. Node ya no lee ningún
   archivo de tests/reference: completados el motor y los cuatro auxiliares.
   El piloto de Ejecutivo AER ya está terminado; seguir otros bloques y
   la auditoría final de consumidores. Preservar entradas, casos límite y cobertura; comprobar que
   las pruebas detectan alteraciones deliberadas usando copias temporales.
3. Solo después retirar referencias/generadores y transporte de pruebas que
   ya no tengan consumidores. Mantener el registro/servicios internos usados.
4. Mantener pruebas permanentes con rutas de producción y CSP; ejecutar
   regresión final y documentar evidencia antes de cerrar fase 11.
5. Genesis y activación de accesos requieren configuración de despliegue;
   no son una razón para alterar cálculos o habilitar ACCESS_ENFORCED.


## Estructura

- `frontend/templates/layouts/` (`base.html` con el importmap `#app/...`, `app.html` con la barra superior y el bloque `freshness`), `partials/`, `pages/`.
- `frontend/static/styles/`: `tokens.css`, `base.css`, `layout.css`, `components.css`, `a11y.css` y `pages/*.css` (una hoja por pantalla; `ds.css`, `legacy-base.css`, `portal-controls.css`, `portal-loading.css`, `agreements.css`, `period-picker.css` son compartidas con el diseño anterior).
- `frontend/static/scripts/`: `data/` (cliente de la API), `lib/`, `ui/` (componentes reutilizables), `pages/<pantalla>/main.js` + `sections/`.
- Todo módulo compartido (fuera de `pages/`) **debe estar en el importmap** de `layouts/base.html` (hay una prueba que lo exige).
- `apps/portal/pages.py`: vistas de las páginas nuevas. `apps/portal/views.py`: servicios de contexto y entradas conservadas para API/precarga. `apps/portal/api/`: API v1 (`{data, meta}`).
- Colores en `styles/*.css` solo por variables de `tokens.css` (los de `pages/` pueden ser literales). Sin `style=""` ni scripts ejecutables en línea; el importmap del layout lleva nonce y CSP ya bloquea por defecto.

## Receta por pantalla

1. **Plantilla.** Hay dos caminos:
   - *Datos por API* (si existe `screens/...`): el JS pide los datos con `apiGet` y pinta con `el()` de `lib/dom.js` (nunca `innerHTML` con datos).
   - *Contexto Python conservado*: `_current` fija `request.portal_template` para vistas que usan `render_page`. Comercial usa `comercial_response` con su plantilla vigente explícita. No restaurar `_modern` ni cambiar servicios/cálculos para simplificar esta capa.
2. **Herramientas** en `tools/migracion/` (ejecútalas desde la raíz; ajusta rutas `shots_tmp/` → `tools/migracion/` si hace falta):
   - `migrate_page.py <legacy.html> <nombre> <body_class> [hoja.css…]` arma la plantilla, la hoja (sin reglas de la barra superior) y guarda los scripts en línea para portarlos a mano.
   - `inline2css.py` pasa `style=""` a clases `.x.x` (misma fuerza que el estilo en línea). Los estilos con `{{ }}` hay que resolverlos a mano (por ejemplo con `data-width` y JS).
   - `scope_css.py` prefija reglas con una clase si la hoja anterior tiene reglas globales.
3. **Ruta.** Las rutas de `apps/portal/pages.py` ya sirven frontend; no restaurar bifurcaciones de comparación en producción. La referencia antigua se monta solo desde pruebas.
4. **Comparaciones.** El detalle anterior se conserva solo en tests/reference; las otras pantallas tienen referencias guardadas. Congelar con los mismos datos y comprobar cajas, estilos, cifras e interacciones. No regenerar esperados desde la implementación nueva para hacer pasar una diferencia. Los scripts locales test_zz/diff.py son auxiliares y no se comitean. Fugas visuales históricas:
   - `box-sizing`: la pantalla anterior no usaba `border-box` (`base.css` ya lo excluye bajo `body.ds`).
   - `th`/`td`/`.card`/`.note` de `components.css` agregan estilos que la anterior no tenía.
   - `.page` de `layout.css` suma relleno: neutralízalo con `body.<clase> main.page { max-width: none; padding: 0; }` y `body #main-content { margin-left: 0 !important }` (ya está en `legacy-base.css`).
   - Pantallas con captura (Business Overview, Operativa, Comercial) montan `mountPageCapture` en `.fresh`.
5. **Pruebas.** Conservar estructura, filtros, regreso, error/reintento y alcance limitado. Las comparaciones del detalle anterior usan `tests/reference` hasta congelarlas; no parchear funciones retiradas. Validar también rutas reales y CSP, sin reference_site.
6. **Plan y commit.** Actualiza el plan con evidencia y haz un commit por pantalla.

## Cómo probar (Windows, Git Bash)

```bash
export MSYS_NO_PATHCONV=1
.venv/Scripts/python -m pytest tests/portal tests/core tests/access tests/e2e -q --no-cov
.venv/Scripts/ruff check apps core config tests --exclude 'test_zz_*.py'
.venv/Scripts/ruff format --check apps tests
.venv/Scripts/mypy apps/portal/pages.py
node --test tests/frontend/*.test.*
```

- Las pruebas e2e usan Playwright con la red bloqueada; el fixture `datos` de `tests/e2e/conftest.py` pone datos de ejemplo.
- No correr dos procesos pytest con base de pruebas simultáneamente. Aplicar formato solo a archivos propios; no reformatear temporales ajenos. No afirmar una suite completa por sumar corridas con alcances distintos.
- Al escribir archivos largos con comandos de shell, evita heredocs con comillas simples; usa el editor de archivos.

## Cuidado

- `vista=` en Costos elige proyectos/márgenes. `?anterior=1` es un enlace obsoleto que debe seguir mostrando la pantalla vigente, no restaurar la plantilla retirada.
- Cualquier `?bloque=consumos` o JSON que antes devolvía la vista de la cuenta ahora lo da la API; no lo restaures.
- No hay `ACCESS_ENFORCED` por defecto: las pruebas con permisos usan los fixtures `enforced` y `DictProvider`.
