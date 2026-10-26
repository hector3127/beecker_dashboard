# Plan de migración del frontend

Objetivo: HTML, CSS y JavaScript modular sobre Django, con el mismo
funcionamiento, listo para llevarse a Genesis y con permisos que Django valida
(`docs/permisos.md`). La integración con Genesis sigue pendiente de sus
respuestas; la migración del frontend sí avanza.

## Estado real (23/10/2026)

Tres cosas distintas, que no se confunden:

- **API**: existe `screens/…` con permiso y alcance validados en el servidor.
- **Frontend migrado**: la ruta activa (`apps/portal/urls.py`) sirve una
  plantilla de `frontend/templates/` con CSS y JS separados de `frontend/static/`.
- **Validación visual**: capturas lado a lado (anterior contra nueva) con los
  mismos datos. Los snapshots de texto de `tests/e2e` no la sustituyen.

Una pantalla solo cuenta como migrada si cumple las tres.

| Fase | Entrega | API | Frontend migrado | Estado |
|---|---|---|---|---|
| 0 | Línea base e2e | n/a | n/a | Hecha |
| 1 | `frontend/`: layouts, tokens, cliente de datos, importmap | n/a | Hecha | Hecha |
| 2 | App `access`: capacidades y alcance | Hecha | n/a | Hecha; apagada por defecto |
| 3 | EVA-04 | Hecha | Hecha | Hecha (validación visual 23/10; rediseño corregido al anterior) |
| 4 | Operativa | Hecha | Hecha | Hecha (validación visual 23/10) |
| 5 | Acuerdos | Hecha | Componente modular compartido en Cuenta y Business Overview | Integrado; conservar pruebas de acciones y permisos |
| 6 | Línea base de lo nuevo | n/a | n/a | Hecha |
| 7 | Comparativa, cuenta, Delivery Manager | Hecha | Hecha | Hecha (23/10) |
| 8 | Business Overview, diccionario, KPIs de DMs | Hecha | Hecha | Hecha (23/10) |
| 9 | Resto de pantallas | APIs de EVA 1-3 (incluidos históricos y consumos), Inversión, Capacidad mensual y diaria, las cuatro vistas de Facturabilidad y Costos; varias pantallas conservan contexto de servidor | **Hecha**: Comercial, Todas las cuentas, Costos, Inversión, ambas pantallas de Capacidad, Facturabilidad, EVA 1–3 y Proyecto simple | Hecha; Proyecto simple conserva contexto Python, con comparación visual y pruebas |
| 10 | `proyecto_detalle` y fin de `/api/rpc/` | API v1 para pestañas migradas, incluidas lecturas y acciones IA AER; auxiliares compartidos aún por retirar | **Parcial**: ambos Ejecutivos, Cliente, Acciones, Planeación, Esfuerzo, Recursos e IA; Riesgos AER y RAID/Azure/Comunicación IXS usan módulos. Falta estructura/estado/auxiliares compartidos | **Parcial**, no completada |
| 11 | Limpieza y CSP obligatoria; permisos/Genesis como decisión de despliegue | n/a | **No** | **Pendiente** |

**Antecedente del cambio de alcance.** Las primeras versiones nuevas de las
fases 7 y 8 se devolvieron al diseño anterior por pedido del usuario. Después
se migraron conservando ese diseño: hoy sus rutas activas usan `frontend/`,
como indica la tabla por pantalla. Las anteriores se mantienen temporalmente
para comparar, sin confundir su existencia con la ruta activa.

### Pantallas, una por una

Evidencia: ruta en `apps/portal/urls.py` → vista → plantilla servida.

| Pantalla | Ruta | Plantilla servida | API | Frontend migrado | Validación visual |
|---|---|---|---|---|---|
| Guía de interfaz | `guia-de-interfaz/` | `pages/guia.html` | `me`, `ping` | **Sí** | n/a (es nueva) |
| Operativa | `operativa/` | `pages/operativa.html` | `screens/operativa/…` | **Sí** | **Hecha 23/10**: barra, encabezado y tarjetas medidos contra la anterior |
| EVA-04 | `operativa/eva-4/` | `pages/eva4.html` (la anterior con `?vista=anterior` hasta el 3/11) | `screens/eva4/` | **Sí** | **Hecha 23/10**: se rehízo con el diseño anterior (encabezado con mes, indicadores, dos columnas, sin plegables) |
| Horas por mes (cuenta) | `cuenta/<slug>/horas/` | `pages/account_hours.html` | `screens/cuenta/horas/` | **Sí** | n/a (funcionalidad nueva, del usuario) |
| Business Overview | `` (raíz) | `pages/executive.html` (la anterior con `?vista=anterior`) | `screens/executive/`, `agreements/` | **Sí** | **Hecha 23/10**: estilos calculados y cajas iguales; `tests/e2e/test_ejecutiva.py` |
| Cuenta | `cuenta/<slug>/` | `pages/account.html` (la anterior con `?vista=anterior`) | `screens/cuenta/…`, `agreements/` | **Sí** | **Hecha 23/10**: estilos calculados y cajas iguales; `tests/e2e/test_cuenta.py` |
| Comparativa de márgenes | `ejecutiva/oportunidades/` | `pages/margins.html` (la anterior con `?vista=anterior`) | `screens/margenes/…`, `costs/project/` | **Sí** | **Hecha 23/10**; `tests/e2e/test_margenes.py` |
| Delivery Manager | `operativa/delivery-manager/<slug>/` | `pages/delivery_manager.html` (la anterior con `?vista=anterior`) | `screens/delivery-managers/…` | **Sí** | **Hecha 23/10**; `tests/e2e/test_delivery_manager.py` |
| KPIs de DMs | `operativa/kpis-delivery-managers/` | `pages/kpis_dm.html` (la anterior con `?vista=anterior`) | `screens/kpis-dm/` | **Sí** | **Hecha 23/10**; `tests/e2e/test_kpis_dm.py` |
| Diccionario | `diccionario-datos/` | `pages/dictionary.html` (la anterior con `?vista=anterior`) | `reference/glossary/` | **Sí** | **Hecha 23/10**; `tests/e2e/test_diccionario.py` |
| Todas las cuentas | `ejecutiva/cuentas/` | `pages/all_accounts.html` (la anterior con `?vista=anterior`) | No (datos por el contexto de la vista) | **Sí** (plantilla modular) | **Hecha 24/10** |
| Costos | `ejecutiva/costos/detalle/` | `pages/costs.html` (la anterior con `?anterior=1`) | `costs/summary/`, `costs/project/` | **Sí** | **Hecha 24/10**; `tests/e2e/test_costos.py` |
| Comercial | `comercial/` | `pages/commercial.html` (la anterior con `?vista=anterior`) | No (datos por el contexto de la vista) | **Sí** (plantilla modular) | **Hecha 24/10**; `tests/e2e/test_comercial.py` |
| Inversión | `operativa/inversion/` | `pages/investment.html` (anterior con `?vista=anterior`) | `screens/inversion/`; la página conserva el contexto del servidor | **Sí** | Comparación de cajas y estilos con los mismos datos a 1450, 900 y 390 px; `tests/e2e/test_inversion.py` |
| Capacidad: asignaciones mensuales | `operativa/capacidad-instalada/` | `pages/capacity.html` (anterior con `?vista=anterior`) | `screens/capacidad/`; mantiene formulario GET y CSV del servidor | **Sí** | `tests/e2e/test_capacidad.py`: filtros, CSV y comparación de cajas/estilos a 1450 y 390 px |
| Capacidad: detalle diario | `capacidad-instalada/` | `pages/capacity_daily.html` (anterior con `?vista=anterior`) | `screens/capacidad/diaria/` y `.../proyecto/` | **Sí** | `test_capacidad_diaria.py`: matriz y recursos a 1450 y 390 px; filtros, CSV, paginación, reintento, mes y fuentes parciales |
| Facturabilidad (general, especialidad, recurso) | `operativa/facturabilidad/…` | `pages/billability.html`, `billability_specialty.html`, `billability_resource.html` (anteriores con `?vista=anterior`) | `screens/facturabilidad/…`; se conserva el contexto del servidor | **Sí** | `test_facturabilidad.py`: cifras, periodos, áreas, pestañas, regreso, errores y comparación a 1450 y 390 px, con selectores abiertos y cerrados |
| Facturabilidad por área | `operativa/facturabilidad/area/` | `pages/billability_area.html` (anterior con `?vista=anterior`) | `screens/facturabilidad/area/{areas,mes,lote,cache,ids}/` | **Sí** | `test_facturabilidad_area.py`: General, Detalle recurso, KPIs, % Recurso y Detalle HRS, además de área seleccionada; comparación de tablas, cajas y estilos a 1450 y 390 px |
| EVA 1 y su histórico IXB/RaaS/SaaS | `operativa/eva-1/`, `operativa/eva-1/cerrados/` | `pages/eva1.html`, `partials/eva_closed.html` | `screens/eva-1/cerrados/`; conserva contexto de servidor en la página | **Sí** | `test_eva123.py`: filtros, CSV, carga diferida, reintento y comparación de tablas, cajas y estilos a 1450 y 390 px; histórico original y nuevo |
| EVA 2 | `operativa/eva-2/` | `pages/eva2.html` | `screens/eva-2/`; conserva contexto de servidor | **Sí** | `test_eva123.py`: mismas tablas, colores, cifras y estados vacíos a 1450 y 390 px. No tenía desplegable de cerrados y no se añadió |
| EVA 3 e histórico AER/T&M | `operativa/eva-3/`, `operativa/eva3/cerrados/` | `pages/eva3.html`, `partials/eva3_closed.html` | `screens/eva-3/{consumos,cerrados,cerrados/consumo}/` | **Sí** | `test_eva123.py`: consumo diferido, errores parciales, reintento del guardado y comparación de tablas/cajas/estilos a 1450 y 390 px |
| Proyecto simple | `proyecto/<id>/` | `pages/project.html` (anterior con `?vista=anterior`) | No; conserva el contexto de servidor y su alcance por cuenta | **Sí** (plantilla modular) | `test_proyecto_simple.py`: cifras, barras, riesgos, equipo, historial, regreso, errores parciales y comparación de cajas/estilos a 1450 y 390 px |
| Detalle del proyecto | `proyectos/<id>/` | `pages/project_detail.html`; entrada, ambos Ejecutivos, Esfuerzo, Recursos y presentación/cargas/editores de Planeación IXB modulares | `screens/proyectos/filtros/`, `screens/proyectos/<id>/{ejecutivo,aer,raid,tasks,etapas,recursos,registros,planeacion}/`, `.../recursos/guardar/`, `.../planeacion/azure/`, `.../planeacion/<tipo>/{guardar,eliminar}/`; resto RPC | **Parcial**, acciones restantes de Planeación y otras pestañas anteriores | Entrada AER e IXB a 1450/390 px; ambos Ejecutivos, Esfuerzo, Recursos y presentación/editores de Planeación IXB a 1450/900/390 px; otras pestañas pendientes |

«Igual» significa que sigue la plantilla anterior, no que se haya migrado. En
`apps/portal/templates/portal/` quedan 33 plantillas, 17 scripts y 16 hojas de
estilo anteriores. Tras Inversión y Capacidad mensual, `frontend/templates/pages/`
contiene 25 plantillas: las 24 modulares anteriores (incluida la guía) y la
entrada transitoria de Detalle. Esta última no suma otra pantalla completada.
Incluye también los fragmentos de `partials/`.

### Fase 10: inventario pendiente por pestaña

Estimación orientativa al 25/10/2026: **alrededor del 85%**, por alcance
funcional revisado, no por líneas de código ni como criterio de aceptación.
Las pestañas principales están migradas; el cierre incluye compatibilidad
genérica/sin proyecto, arranque sin el script anterior y validación final.
El porcentaje no significa que el detalle ya sea independiente.

Terminados: ambos Ejecutivos, Cliente, Acciones, Planeación, Esfuerzo, Recursos e IA de ambas familias; Riesgos AER;
Gestión RAID, Azure DevOps y Centro de Comunicación IXB/SaaS/RaaS.
También están separados el editor de hitos históricos y la ventana de
comunicados (incluida extensión); ver el traspaso para su evidencia y alcance.
La entrada modular usa API para filtros y dashboards. Encabezados, navegación,
refresco, montaje e inicialización de proyectos usan módulos. Los doce valores
centrales y siete estados de paneles pertenecen a `project_state.js`; siguen
otros adaptadores, compatibilidad y auxiliares enlazados al script anterior.
La entrada de proyectos y sus mensajes ya usan módulos.

| Familia | Apartados que faltan por modularizar y validar |
|---|---|
| IXB/SaaS/RaaS | Integración de estructura/estado y auxiliares compartidos (ver fila Compartido) |
| AER/T&M | Integración de estructura/estado y auxiliares compartidos; pestañas ya modulares |
| Compartido | Contextos/adaptadores restantes, compatibilidad sin proyecto/Ejecutivo genérico y soporte; retirar dependencia de `proyecto_detalle.js` y del shim RPC en la ruta nueva. Estados centrales/paneles identificados y contextos Planeación/Esfuerzo/Recursos AER ya separados |

Planeación IXB se está separando por bloques: primero el transporte de
vacaciones/compromisos y su panel Azure; después modelo, vista y controlador,
incluidos Gantt editable, calendario, editores y extensión de proyecto.
Los editores de vacaciones y actividades/hitos, la presentación general y
sus consultas y las escrituras de Work Items ya son modulares. El editor de
hitos del histórico y los comunicados también están separados. Azure DevOps
ya usa API, estructura, resumen, agrupaciones, tabla y acciones modulares.
Comparte controles con Planeación y conserva sus diferencias de presentación
y guardado de fechas; no ejecuta las funciones anteriores de esa pestaña.
Usar API no equivale a migrar toda una pestaña.
Planeación conserva puentes de estado en el archivo anterior. Los auxiliares
`ixsEditarHitoTimeline`, `_ixsCargarEstadosRecursos` y `_ixeAuto` ya delegan en
`ixs_support{,_model}.js`; no reabrir su vista y editores. Falta retirar los
adaptadores/almacenamiento compartidos y la compatibilidad genérica.
El retiro de archivos anteriores del repositorio y la CSP obligatoria
pertenecen a la fase 11, posterior a completar este detalle.

### Encabezado y seis indicadores genéricos (25/10/2026)

`generic_header_model.js` conserva la presentación de metadatos, defaults,
presupuesto, umbral de ritmo, etiquetas de cierre y fecha PRD/estimada.
`generic_header_view.js` usa DOM seguro y SVG nativo para el mini-donut; estilos
en `project_detail_generic_header.css`. Preserva el ID del indicador financiero.
No cambia cifras, cálculos de negocio, API ni permisos.

El renderer transitorio suministra los flags de color/riesgo/cierre y monta
ambos componentes en marcadores estáticos; la ruta nueva no construye su HTML
anterior ni llama al helper HTML del mini-donut. El resto genérico sigue
pendiente: gráficas, fuentes, acciones y coordinación final. No marcar la
pantalla completa ni retirar todavía script/shim.

Evidencia: **57 pruebas únicas de navegador aprobadas**: 25 de encabezado/KPIs,
12 de modelo/fallback de pantalla moderna y 20 de entrada/pestañas/recarga.
Se compara contra la anterior a 1450/900/390 px, con datos completos/faltantes,
cierre y salida no PRD, mismo ancho y cajas relativas. SVG namespace/estilos
y texto seguro con `innerHTML` bloqueado comprobados; ID financiero conservado.
Cuatro Node nuevos contrastan mini-donut con el helper original y prueban umbral,
cierre, defaults, strings numéricos y salida PRD/estimada: suite completa
**437 aprobadas y tres fallos anteriores** (`cost_sprint_details`,
`executive_report`, `financial`). Capturas en
`tmp/migration/project_detail/generic_header/` y `generic_timeline/`; cierre
escritorio y metadatos faltantes móvil inspeccionados. Ruff/formato, sintaxis JS,
Django y diff aprobados. Proveedores simulados/red bloqueada, sin consultas
reales ni push; temporales/cambios ajenos intactos.

Observación heredada: fecha sin hora `2026-08-01` se presenta como `31 jul 2026`
en el entorno local por `new Date`/zona horaria; referencia y módulo coinciden.
Se registra para revisión funcional posterior, sin cambiar reglas de fechas.

**Siguiente:** gráficas/fuentes/acciones genéricas; casos sin proyecto/cuenta
y arranque independiente. Fase 10 parcial.

### Tabla de recursos y resumen de hitos genéricos (25/10/2026)

`generic_panels_model.js` conserva la presentación original de filas/totales,
redondeo, clasificación de estados, formato de fechas, notas y agrupación de
hitos. `generic_panels_view.js` construye tabla y resumen con DOM seguro y CSS
externo `project_detail_generic_panels.css`. No cambia cálculos ni permisos.

El renderer transitorio monta estos componentes en marcadores estáticos y no
ejecuta su HTML anterior. Se preservan IDs de tarjeta/rango Clockify para los
enriquecimientos existentes. El resto del Ejecutivo genérico sigue pendiente:
encabezado/KPIs, gráficas, fuentes y acciones. No marcar la pantalla completa.

Evidencia: **51 pruebas únicas de navegador aprobadas**: 19 de paneles,
12 de modelo/fallback de la pantalla moderna y 20 de entrada/pestañas/recarga.
Los paneles se comparan contra la anterior a 1450/900/390 px, con datos,
vacíos, notas y suspensiones; mismo ancho de referencia y cajas relativas por
el contenedor aún pendiente. Se verifica uso de clases modulares y texto seguro
con `innerHTML` bloqueado, conservando el destino del rango Clockify. Cuatro Node
nuevos contrastan estados/fechas con los helpers originales y verifican defaults,
redondeo, orden, notas y ausencia de mutación. Suite completa **433 aprobadas y
tres fallos anteriores** (`cost_sprint_details`, `executive_report`, `financial`).
Capturas en `tmp/migration/project_detail/generic_panels/` y `generic_timeline/`;
recursos escritorio e hitos con notas inspeccionados. Ruff/formato, sintaxis JS,
Django y diff aprobados. Proveedores simulados/red bloqueada, sin consultas
reales ni push y con temporales/cambios ajenos intactos.

**Fase 10 parcial.** Mantener script/shim; después del genérico faltan casos
sin proyecto/cuenta y arranque independiente.

### Vista aislada de la línea temporal genérica (25/10/2026)

`generic_timeline_view.js` dibuja eje/meses, barras, estados, marcadores y
leyenda con DOM seguro a partir del modelo temporal existente. Sus estilos
fijos están en `project_detail_generic_timeline.css`; geometría/colores de
estado usan CSSOM. No cambia reglas, fechas, API ni permisos.

El renderer transitorio sustituye un marcador estático por este componente;
la ruta nueva no ejecuta el constructor HTML anterior del Gantt. El resto
de la vista genérica sigue anterior. Las diferencias de botones detectadas
entre plantillas siguen pendientes fuera de este componente: la fase 10 y
la vista genérica completa no se marcan terminadas.

Evidencia: **45 pruebas de navegador aprobadas**. Trece del componente:
comparación de contenido/cajas/estilos contra la anterior a 1450/900/390 px,
con hitos, cierre y sin hitos; y texto seguro con `innerHTML` bloqueado.
Ambas versiones se alojan en el mismo ancho original y se comparan posiciones
relativas: las diferencias externas del contenedor genérico siguen pendientes.
Doce comparaciones de modelo/fallback conservan la pantalla moderna completa;
20 adicionales verifican entrada/pestañas/recarga. Suite Node **429 aprobadas
y tres fallos anteriores** (`cost_sprint_details`, `executive_report`,
`financial`). Capturas en `tmp/migration/project_detail/generic_timeline_view/`
y `generic_timeline/`; hitos escritorio y cierre móvil inspeccionados.
Ruff/formato, sintaxis JS, Django y diff aprobados. Proveedores simulados/red
bloqueada, sin consultas reales ni push y con cambios/temporales ajenos intactos.

**Siguiente:** resto de vista/controlador/CSS genéricos, fuentes/formularios,
casos sin proyecto/cuenta y arranque independiente. Mantener script/shim.

### Modelo temporal del Ejecutivo genérico (25/10/2026)

`generic_timeline_model.js` separa el cálculo temporal original: fases repetidas,
suspensiones, estados, asignación de hitos adicionales, resumen, detección de
finalización, rango y meses. Reutiliza los helpers de categoría/nombre ya
contrastados. No modifica los datos recibidos ni cambia reglas/fechas.

El renderer de compatibilidad usa el modelo nuevo; el bloque original queda
como fallback para comparación. **La vista genérica sigue pendiente**: aún
tiene HTML/eventos/estilos y enriquecimientos anteriores. Se detectó una
diferencia previa entre plantillas (botones de 25 frente a 44 px). Por eso la
comparación incremental modelo/fallback usa la misma plantilla moderna;
no cuenta como validación visual final contra `?vista=anterior` ni como vista
migrada. La corrección de esas diferencias corresponde al bloque de vista.

Evidencia: dos Node nuevos comparan 79 combinaciones contra el bloque original,
incluidas fechas de corte, fases repetidas, límites de suspensión, tipos de
marcador y cierre/cancelación; no mutan los datos. Suite completa **429
aprobadas y tres fallos anteriores** (`cost_sprint_details`, `executive_report`,
`financial`). **32 de navegador aprobadas**: 12 comparan modelo/fallback bajo
la misma plantilla a 1450/900/390 px y el resto verifica entrada/pestañas/recarga.
La vista genérica **no** se marca completada. Capturas en
`tmp/migration/project_detail/generic_timeline/` (`fallback.png`/`model.png`);
escritorio inspeccionado. Ruff/formato, sintaxis JS, Django y diff aprobados.
Proveedores simulados/red bloqueada, sin consultas reales ni push y con cambios/
temporales ajenos intactos.

**Fase 10 parcial.** Siguiente: vista/controlador/CSS genéricos y sus fuentes/
formularios; después casos sin proyecto/cuenta y arranque independiente.
Mantener script/shim. Estimación orientativa de fase: alrededor del 85%.

### Contexto y recarga directos del proyecto (25/10/2026)

`project_entry_runtime.js` compone el contexto de entrada con el almacén y
renderers AER/IXS directos. La recarga de hitos en Planeación IXS pide al
controlador de entrada que use la selección actual y conserva sus errores/
reintentos. Los callbacks de sin proyecto/cuenta, cambio de cliente y Ejecutivo
genérico permanecen explícitos, sin cambiar sus ramas ni cálculos.

Los contextos AER compartidos llegan directamente al runtime IXS desde AER.
Se retira `ixsRuntimeBindings` y su conexión previa; la vista anterior permanece
inyectada desde main hasta migrar el Ejecutivo genérico. No se altera API,
permisos, modelos ni diseño; no se declara independiente todo el detalle.

Evidencia: **33 pruebas de entrada/sesión/pestañas y 72 adicionales aprobadas
(105 de navegador total)**. Incluyen hitos, shell, Cliente/Acciones IXS,
runtimes AER/IXS y soporte; comparación en tres tamaños, reintentos y respuestas
tardías. Dos nuevas bloquean cinco entradas anteriores y guardan un hito,
recargando directamente y reintentando ante 503; verifican payload/ID/índice
exactos y vuelta a Ejecutivo IXS. Tres Node nuevos verifican contexto/estado,
renderers y fallbacks. Suite completa **427 aprobadas y tres fallos anteriores**
(`cost_sprint_details`, `executive_report`, `financial`). Ruff/formato, sintaxis
JS, Django y diff aprobados. Capturas en `tmp/migration/project_detail/entry/`,
`session/`, `tabs/`, `ixs_milestones/`, `shell/` e `ixs_client_actions/`;
entrada IXS escritorio y AER móvil inspeccionadas. Proveedores simulados/red
bloqueada, sin consultas reales, sin push y con temporales/cambios ajenos intactos.

**Fase 10 parcial.** Siguiente: vista anterior/Ejecutivo genérico, sin proyecto/
cuenta y arranque independiente. Mantener aún script/shim.

### Recomendación IA → alta RAID modular compartida (25/10/2026)

El runtime IXS conecta `raidOpen`/`raidManual` con `project_ixs_tools.js`, que
usa el mismo `beeIxsRaidCreator` de Gestión RAID. Su apertura manual reutiliza
el handler existente del creador. Conserva tipo, texto de título/detalle unido
con raya, guardia por ID y recarga del registro tras crear. No cambia modelos,
campos, endpoints, permisos ni reglas; no publica automáticamente.

`ixsRuntimeBindings` deja de proporcionar las entradas RAID anteriores. Estas
siguen intactas para comparar, pero el enlace IA→RAID no las ejecuta. La ruta
nueva usa API v1 y exige pulsar Crear, igual que el formulario modular existente.

Evidencia: **108 pruebas de navegador aprobadas** de IA→RAID, alta/registro
RAID y vistas/acciones IA. Incluyen los tres tipos a 1450/900/390 px y una
creación simulada de Issue desde IA. Cinco funciones anteriores se bloquean;
se conserva descripción exacta, no hay RPC ni publicación automática.
Una comparación intermitente de Oportunidad pasó al repetirla; se espera
explícitamente la carga y el pintado y se guardan JSON de diagnóstico, sin
relajar igualdad de contenido/cajas/estilos. Capturas en
`tmp/migration/project_detail/ixs_ai_raid/`, `ixs_raid_create/`, `ixs_raid/`
e `ixs_ai_full/`; Issue escritorio y Risk móvil inspeccionados.
Un Node nuevo y comprobaciones ampliadas del runtime: suite completa
**424 aprobadas y tres fallos anteriores** (`cost_sprint_details`,
`executive_report`, `financial`). Ruff/formato, sintaxis JS, Django y diff
aprobados. Proveedores simulados/red bloqueada, sin consultas ni publicaciones
reales, sin push y con temporales/cambios ajenos intactos.

**Fase 10 parcial.** Siguiente: vista anterior/recarga, compatibilidad
genérica/sin proyecto y arranque independiente. Mantener aún script/shim.

### Herramientas compartidas IXS: Planeación, Comunicados y CSS (25/10/2026)

`project_ixs_tools.js` conecta el runtime con el editor de Planeación y la
ventana Comunicados directamente. Mantiene decodificación de UID, tipo inicial,
estado compartido, guardia de proyecto y repintado tras guardar. Comunicados
conserva ID de Planeación, nombre del proyecto, familia y fechas sugeridas por
el modelo existente. No cambia API, permisos ni modelos de cálculo.

Los estilos AER/IXS/IA ya están enlazados en la plantilla; el runtime no llama
a los inyectores del archivo anterior. `ixsRuntimeBindings` deja de aportar
estilos, editor y Comunicados. Conserva RAID, vista anterior y recarga.

Evidencia: **94 pruebas de navegador aprobadas** de runtime IXS, editores,
Comunicados, sesión, Planeación y fuentes IA; comparación en tres tamaños,
guardados/UID exacto, errores/reintentos y respuestas tardías. La prueba nueva
bloquea siete funciones anteriores, guarda vacaciones y abre Comunicados por UI.
La prueba de sesión conserva orden/estado y verifica enlaces CSS externos en
vez del inyector. Tres Node nuevos y comprobaciones ampliadas del runtime:
suite completa **423 aprobadas y tres fallos anteriores** (`cost_sprint_details`,
`executive_report`, `financial`). Ruff/formato, sintaxis JS, Django y diff
aprobados. Capturas en `tmp/migration/project_detail/ixs_planning_editor/`,
`communique/`, `session/`, `ixs_planning_view/` e `ixs_ai_sources/`; editor y
Comunicado inspeccionados. Proveedores simulados/red bloqueada; sin consultas
ni correos reales. Sin push y con temporales/cambios ajenos intactos.

**Fase 10 parcial.** Siguiente: esos enlaces residuales, compatibilidad
genérica/sin proyecto y arranque independiente. No retirar aún script/shim.

### Coordinación directa AER/T&M (25/10/2026)

`project_aer_runtime.js` conecta sesión, shell, pestañas, almacén, paneles y
contratos de funciones directamente. Monta/navega/refresca, conserva la pestaña
al actualizar y el alias minutas→IA. Las cinco lecturas IA mantienen su orden
análisis/minutas/configuración/resumen/pendientes. Formularios y fuentes/acciones/
presentación IA reciben sus controladores actuales, sin callbacks anteriores.
Comunicados abre su módulo con el ID/nombre/familia originales.

Cliente/Acciones IXS recibe los contextos AER compartidos desde el coordinador
nuevo; deja de depender de `projectTabsContext`. Las entradas AER anteriores
delegan para compatibilidad, pero los eventos y cargas del coordinador no las
ejecutan. Los CSS ya están enlazados en la plantilla nueva: no requiere inyección.
No cambian modelos, API, cifras, permisos, navegación ni reglas de negocio.

Evidencia: **31 pruebas de entrada/sesión/montaje y 147 adicionales de
navegador aprobadas (178 total)**. Cubren shell, fuentes/acciones IA AER,
Cliente/Acciones IXS, formularios de Planeación, Recursos y Riesgos; comparan
contra la anterior a 1450/900/390 px y prueban errores/respuestas tardías.
La prueba nueva bloquea quince entradas anteriores y navega IA→refresco→Ejecutivo.
Los dobles del shell observan el coordinador nuevo con los mismos conteos/orden.
Cuatro Node nuevos; suite completa **420 aprobadas y tres fallos anteriores**
(`cost_sprint_details`, `executive_report`, `financial`). Ruff/formato, sintaxis
JS, Django y diff aprobados. Capturas en `tmp/migration/project_detail/`;
shell y Recursos móvil inspeccionados. Proveedores bloqueados/simulados, sin
consultas ni correos reales, sin push y con temporales/cambios ajenos intactos.

**Fase 10 parcial.** Siguiente: callbacks IXS restantes (estilos, editores,
RAID, vista anterior y recarga), compatibilidad genérica/sin proyecto y arranque
independiente. No retirar todavía script/shim ni reabrir pestañas migradas.

### Coordinación directa de renderizado/navegación IXS (25/10/2026)

`project_ixs_runtime.js` conecta shell, pestañas, sesión, almacén, soporte y
adaptadores IXS directamente. Monta/selecciona/refresca, abre/pinta IA, carga sus
fuentes en el orden previo y aloja Cliente/Acciones con su caché y presentación
AER compartida. Conserva reinicio a Ejecutivo e invalidación de caché al refrescar.
Los callbacks de recursos y marcadores usan directamente sus módulos.

`project_ixs_adapters.paint` usa la vista y paneles IA modulares con las mismas
guardias de target/pestaña/proyecto/estado. La navegación de la vista y las cargas
diferidas repintan por el coordinador, sin pasar por los renderizadores previos.
Las entradas anteriores IXS delegan; `ixsRuntimeBindings` aún suministra estilos,
contextos AER compartidos, editores, Comunicados, RAID y recarga.

**Fase 10 parcial.** Siguiente: coordinación AER y cierre de los callbacks/
entradas de compatibilidad; después Ejecutivo genérico/sin proyecto y arranque
independiente. No retirar script/shim ni declarar independiente todo el detalle.

Evidencia inicial: **31 pruebas de entrada/sesión/montaje aprobadas**. Se
actualizan dobles que interceptaban funciones previas para que intercepten
controladores/runtime actuales; conservan identidad, orden y conteos. Cuatro
Node nuevos verifican coordinación/refresco/caché y guardias de pintura IA.
Suite completa **416 aprobadas y tres fallos anteriores** (`cost_sprint_details`,
`executive_report`, `financial`).

**108 adicionales de navegador aprobadas** de coordinación, shell, Cliente/
Acciones y fuentes/acciones IA: **139 en total**. Una nueva prueba bloquea
quince funciones anteriores y verifica navegación IA→Ejecutivo y actualización.
Los dobles se conectan a módulos actuales; la observación de paneles intercepta
el argumento de vista real, manteniendo todas las comprobaciones de datos/texto/
estado/navegación. Ruff/formato, Django y diff aprobados. Capturas de entrada,
sesión, pestañas, shell, Cliente/Acciones e IA inspeccionadas. La red de pruebas
bloquea proveedores; sin consultas ni correos reales y sin push.

### Adaptadores IXB/SaaS/RaaS de IA e hitos (25/10/2026)

`project_ixs_adapters.js` conecta el almacén con los modelos IA existentes y
los hitos de `ixs_executive_model.js`. Compone contexto, snapshot, comparación
y capacidad sin ejecutar `_ixsHitos` ni cálculos anteriores en el flujo IA.
No duplica fórmulas. Fuentes/historial/Drive y acciones usan sus controladores
existentes, misma guardia de vigencia, callbacks y paso a creación RAID.

El contexto de soporte de Planeación también usa el almacén. Su editor llama
directamente al módulo de hitos con ID, índice, fecha, observación y recarga
anteriores; no pasa por `editarHitoDesdeCard` en esa ruta. Las entradas previas
delegan y conservan comparación. Se mantiene el callback de recarga original.

**Fase 10 parcial.** Próximo: coordinación directa de pintura, navegación y
arranque/callbacks (por ejemplo la entrada `ixsIAPintar` sigue preparando la vista
modular), luego compatibilidad genérica/sin proyecto y validación independiente.
No rehacer vistas/modelos ni retirar el script/shim antes de cerrar conexiones.

Ocho Node nuevos comparan datos completos con las funciones originales,
incluidos hitos con emoji/observaciones, memoria, soporte del editor, tres cargas
y paso a RAID. **24 de navegador aprobadas** de fuentes IA y soporte compartido.
La prueba de cálculo IA observa el adaptador nuevo y desactiva tanto adaptador
como modelo para leer la referencia anterior; conserva igualdad y trazas.
**63 adicionales de navegador aprobadas** de acciones IA IXS y Planeación:
**87 en total**. Suite Node **412 aprobadas y tres fallos anteriores**
(`cost_sprint_details`, `executive_report`, `financial`). Ruff/formato, Django
y diff aprobados. Capturas en `tmp/migration/project_detail/ixs_ai_sources/`,
`ixs_ai_full/` e `ixs_planning_view/`, inspeccionadas. Sin API/cálculos nuevos,
sin consultas ni correos reales y sin push.

### Contratos específicos de Acciones/Riesgos/IA (25/10/2026)

`project_feature_contexts.js` separa los contratos de Acciones compartidas,
Riesgos AER, fuentes IA, presentación IA y acciones IA AER; centraliza también
la guardia de identidad/proyecto usada por fuentes, historial, Drive y acciones
IA IXS. El módulo usa el almacén existente y callbacks inyectados.

Acciones conserva detección AER/IXS, snapshot, repintado activo, caché de
pendientes y sustitución sin repintado. Riesgos conserva apertura de Acciones.
IA conserva diferencias entre comparar ID, snapshot y estado, incluida recarga
del mismo ID y descarte de otro estado/proyecto. No se cambian contexto/hechos,
fórmulas, servicios, permisos ni llamadas al modelo. Botones y callbacks de la
presentación mantienen sus argumentos.

**Fase 10 parcial.** Los constructores anteriores delegan, pero siguen inyectando
callbacks de presentación/servicios. Quedan adaptadores IXS residuales, conexiones
directas, compatibilidad genérica/sin proyecto y arranque independiente. No
rehacer formularios ni retirar script/shim antes de completar esas conexiones.

Siete Node nuevos comparan los contratos y guardias contra las funciones
originales: Acciones en ambas familias, Riesgos, tres contratos IA AER e IA IXS.
**68 de navegador aprobadas** de Acciones (vistas/formularios/transporte) AER/
IXS y fuentes IA AER, con comparación a 1450/900/390 px. Suite Node **404
aprobadas y tres fallos anteriores** (`cost_sprint_details`, `executive_report`,
`financial`). **110 adicionales de navegador aprobadas** de Riesgos AER,
acciones IA AER y fuentes/acciones IA IXS: **178 en total**. Cubren comparación
en tres tamaños, formularios, guardados, errores y respuestas tardías. Capturas
en `tmp/migration/project_detail/actions_forms/`, `aer_risks/`, `aer_ai_sources/`,
`aer_ai_view/`, `ixs_ai_sources/` e `ixs_ai_full/`, inspeccionadas. Django y diff
aprobados; formato aplicado. Sin consultas/correos reales ni push.

### Contratos compartidos de entrada/sesión/navegación/montaje (25/10/2026)

`project_contexts.js` construye cuatro contratos desde `project_state.js`:
entrada (metadata/secuencia), sesión (getters/setters y caché), shell (snapshot,
pestaña, vigencia por familia, actualización AER/IXS) y montaje (estados diferidos,
sincronización Azure, acciones de Planeación). La codificación del UID del editor
conserva el tratamiento anterior de Unicode, barras y apóstrofes.

Se conserva la actualización AER con su pestaña y el reinicio IXS con invalidación
de Cliente/Acciones. Los cuatro contextos anteriores delegan al módulo en la ruta
activa; todavía suministran funciones de estilo, renderizado, cargas, navegación
y entradas de paneles. El bloque separa la lógica de estado/lifecycle, sin dar
por retirada la conexión con el script anterior.

**Fase 10 parcial.** Siguiente: contextos específicos restantes (Acciones/IA y
adaptadores IXS), conexiones directas a módulos y compatibilidad genérica/sin
proyecto; luego arranque independiente y validación final. No rehacer vistas.

Evidencia inicial: **31 pruebas de navegador aprobadas** de entrada, sesión y
montaje, incluidas comparaciones visuales y recorrido de las 18 pestañas.
Cinco Node nuevos contrastan los cuatro contratos y ambas familias de shell
con las funciones de referencia, incluidas caché, getters/setters y editor.
**51 adicionales de navegador aprobadas** de navegación/refresco, Cliente/
Acciones y almacén: **82 en total**. Suite Node **397 aprobadas y tres fallos
anteriores** (`cost_sprint_details`, `executive_report`, `financial`). Django y
diff aprobados; formato aplicado. Capturas en
`tmp/migration/project_detail/entry/`, `session/`, `tabs/`, `shell/` e
`ixs_client_actions/`, inspeccionadas. Sin consultas/correos reales ni push.

### Avisos y guardado compartidos (25/10/2026)

`project_feedback.js` separa avisos temporales, guardado/recuperación de botón,
selección de botón principal y cierre normal/ancho. La entrada lo registra
antes de cargar el script anterior. `_aerToast`, `_aerStartSaving`,
`_aerPrimaryModalBtn` y los dos cierres delegan en la ruta nueva.

Conserva aviso a los 1800 ms y retirada 220 ms después, éxito/error sin deduplicar,
botón deshabilitado y clase saving tras éxito, restauración tras error y no-op
cuando falta botón. El mensaje se inserta como texto; los nodos originales del
botón se reponen sin interpretar HTML. Prioridad de selección y cierres separados
se mantienen. No se porta el generador anterior `_aerModal(html)` a un parser:
los formularios nuevos ya construyen sus nodos de forma segura.

**Fase 10 parcial.** Siguiente: contextos/adaptadores restantes y sus conexiones
directas a módulos; luego compatibilidad genérica/sin proyecto y arranque sin
archivos anteriores. Los wrappers aún existen para conservar la comparación.

**15 pruebas nuevas de navegador aprobadas**: doce comparaciones de avisos/
guardado/restauración a 1450/900/390 px, dos del temporizador/texto seguro contra
la referencia y una del contrato de éxito/error/botón ausente/cierre separado.
**62 de regresión aprobadas** de Planeación/Recursos/acciones IA AER: **77 de
navegador en total**. Suite Node **392 aprobadas y tres fallos anteriores**
(`cost_sprint_details`, `executive_report`, `financial`). Ruff/formato, Django
y diff aprobados. Capturas en `tmp/migration/project_detail/feedback/`,
inspeccionadas escritorio/móvil. Sin API/cálculos nuevos, sin consultas/correos
reales ni push; cambios ajenos intactos.

### Estados y contextos de paneles (25/10/2026)

`project_state.js` también posee siete estados de paneles: rango y filtros de
Planeación AER, registros Clockify AER y selección de Recursos, Planeación IXS,
Planeación Azure y Azure. Sus declaraciones anteriores se enlazan al almacén
sin reiniciarlo; la ruta de comparación conserva sus literales originales.

`project_panels.js` construye los contextos de Planeación, Esfuerzo y Recursos
AER: snapshot de dashboard, guardias de identidad/pestaña y acceso/sustitución
de rangos, filtros, registros y selección. Conserva las firmas y callbacks de
guardado, repintado, recarga, errores y Comunicados. Los tres contextos previos
solo delegan en la ruta activa. Los callbacks comunes todavía se inyectan desde
el archivo anterior; este bloque no retira esa dependencia.

**Fase 10 parcial.** Siguiente: otros contextos/adaptadores y soporte de guardado/
avisos; después compatibilidad genérica/sin proyecto y arranque independiente.
No rehacer vistas ni cambiar fórmulas, ni retirar script/shim antes de completar
sus dependencias. La tabla de cierre debajo refleja los pendientes actuales.

Diez Node nuevos contrastan los siete valores iniciales y los tres contextos
contra las funciones previas, incluidas guardias y reemplazo de estado. La prueba
del almacén cubre las 19 declaraciones enlazadas. Suite completa: **392 aprobadas
y tres fallos anteriores** (`cost_sprint_details`, `executive_report`, `financial`).

**61 de navegador aprobadas** de identidad del almacén y paneles AER, con
comparación visual a 1450/900/390 px. Cubren filtros/rangos, selección, ventanas,
guardado/borrado y respuestas tardías. Las comprobaciones del almacén en las dos
familias incluyen las siete referencias nuevas. **69 adicionales aprobadas**
de Planeación IXS, tabla Azure y montaje: **130 de navegador en total**.
Ruff/formato, Django y diff aprobados. Capturas en
`tmp/migration/project_detail/aer_planning_controls/`, `aer_effort/`,
`aer_resources/`, `ixs_planning_view/` e `ixs_azure_table/`, inspeccionadas.
Sin cambios de API/cálculos, sin consultas/correos reales ni push.

### Estados centrales del proyecto (25/10/2026)

`project_state.js` crea y almacena doce valores centrales: ambos dashboards,
pestañas y estados IA, Clockify, metadata, secuencia de carga, hitos/ID actual
y caché Cliente/Acciones. Reutiliza las fábricas IA contrastadas contra la
referencia. Cada instancia tiene sus propios objetos/selecciones/cachés.

`main.js` registra el almacén antes del script anterior. Los once nombres
asignables previos se enlazan con accesores temporales; las declaraciones `var`
se limitan al archivo de compatibilidad para no crear otra vinculación léxica.
El caché conserva su referencia constante. Las asignaciones de los callbacks y
los módulos llegan al mismo objeto; no se duplican ni reinician los resultados.
Sin módulo, la comparación sigue inicializando sus valores originales.

**Fase 10 parcial: inventario para el cierre, revisado en código**

| Pendiente | Evidencia y condición de cierre |
|---|---|
| Coordinación restante | IXS ya monta/navega/refresca y pinta IA entre módulos. Falta la coordinación AER y cerrar callbacks aún aportados por compatibilidad: contextos compartidos, estilos/editores/RAID/recarga y arranque. No repetir modelos ni vistas. |
| Compatibilidad genérica | `renderDashboardEjecutivoProyecto` tiene diseño propio para servicios no reconocidos como AER/IXS; ramas sin proyecto/cuenta aún usan funciones previas. Migrar o demostrar sus rutas de entrada antes de retirar dependencias. |
| Conexiones compartidas restantes | Guardado/avisos/cierres ya usan `project_feedback.js`; los contextos todavía inyectan wrappers previos y puentes a editores/hitos. Conectarlos directamente con los módulos al extraer los contextos restantes. |
| Arranque independiente | La plantilla/main todavía carga `gas_shim.js` y `proyecto_detalle.js`. Dejar de cargarlos en la ruta nueva cuando ningún flujo activo los necesite; auditar llamadas reales a RPC, no contar como pendientes todas las ramas guardadas para comparación. |
| Validación final del detalle | Con el arranque independiente, comprobar pestañas, filtros, regreso, exportación, permisos y escrituras; comparación visual e integración sin recursos anteriores ni RPC. |

La eliminación de archivos anteriores del repositorio y CSP obligatoria son
**fase 11**. Genesis/activación de accesos sigue como decisión de despliegue.

Evidencia inicial: **35 de navegador aprobadas** de entrada/sesión/mensajes,
con sus comparaciones visuales. Tres Node del almacén comprueban independencia,
asignaciones bidireccionales y declaraciones reales de compatibilidad sin reset;
el modelo IA conserva el contraste con los literales de referencia. Suite
completa **382 aprobadas y tres fallos anteriores** (`cost_sprint_details`,
`executive_report`, `financial`). **44 de almacén/navegación/pestañas y 69 de
acciones IA AER/IXS/recursos aprobadas**: con las 35 iniciales, **148 distintas
de navegador**. Dos nuevas verifican identidad/sincronización del almacén real.
La comparación IA normaliza scroll cero/dos frames; una primera falla móvil
era solo desplazamiento (cero diferencias de tamaño/texto/estilos). La repetición
completa de acciones aprobó. Ruff/formato, Django y diff aprobados; capturas
inspeccionadas. Sin API/cálculos nuevos, sin consultas/correos reales ni push.

### Auxiliares compartidos IXB/SaaS/RaaS (25/10/2026)

`ixs_support.js` consulta estados de recursos por la API existente: una sola
lectura en vuelo por proyecto, caché tras éxito y reintento tras fallo. La
respuesta actualiza el proyecto capturado; solo repinta Ejecutivo/Planeación/
Esfuerzo si ese proyecto sigue vigente. Reutiliza sus vistas modulares, sin HTML
anterior. `ixs_support_model.js` conserva la normalización de nombres y el valor
de activo (incluidos false y nombres duplicados).

El mismo controlador abre el editor modular de hitos con tipo, índice de origen,
fecha local ISO y observación anteriores. Las fechas sugeridas de Comunicados
separan su modelo, con las mismas prioridades de fases reales/planificadas y
etapa actual. No cambia servicios, fórmulas ni destinatarios.

**Fase 10 parcial.** `ixsSupportContext` conserva getters y el enlace al editor
de hitos. Siguen pendientes almacenamiento/adaptadores y la compatibilidad del
Ejecutivo genérico/sin proyecto. No retirar el archivo anterior ni el shim.

Evidencia inicial: **40 pruebas de Planeación/Ejecutivo aprobadas**, con
comparaciones a 1450/900/390 px, carga diferida y apertura del editor. Once Node
contrastan fechas sugeridas con las funciones originales y prueban estados,
caché en vuelo, reintento, respuesta tardía e índices/fechas del editor. Suite
completa: **379 aprobadas y tres fallos anteriores** (`cost_sprint_details`,
`executive_report`, `financial`). Otras **40 de navegador aprobadas** de
Esfuerzo, Comunicados y lectura compartida de recursos (tres nuevas): **80 en
total**. Capturas en `tmp/migration/project_detail/ixs_planning_view/`,
`ixs_executive/`, `ixs_effort/` y `communique/`, inspeccionadas móvil/escritorio.
Ruff/formato, Django y diff aprobados. Proveedores simulados, sin consultas ni
correos reales; sin push ni cambios ajenos incluidos.

### Entrada de proyectos y mensajes de carga (controlador separado)

`project_entry{,_model,_view}.js` monta la plantilla, carga filtros y selecciona
el proyecto de la ruta antes de consultar su dashboard por API v1. Conserva
prioridad del JSON de ruta sobre el query, ID sin distinguir mayúsculas,
proyectos ausentes de filtros y la clasificación original por servicio/prefijo.
La metadata mantiene sus referencias; `projectEntryContext` la enlaza con los
contextos existentes. El contador de carga es modular e invalida también las
respuestas pendientes de compatibilidad. Solo la respuesta vigente, con su
contenedor conectado, puede reemplazar la pantalla.

Carga, error con reintento y error común (`showError`) usan DOM seguro y eventos
externos. Se conserva el reemplazo global de `showError`, sin cambiar su flujo.
El botón Reintentar neutraliza en CSS externo el tamaño/negrita que añadían los
componentes generales, para coincidir con la referencia anterior.

**Fase 10 parcial.** Se mantienen las ramas sin proyecto/cuenta del panel anterior
y el Ejecutivo genérico que usa un servicio no reconocido como AER/IXS. Siguen
pendientes ese caso, los adaptadores/almacenamiento global, auxiliares de
Planeación y soporte. No retirar script/shim ni dar por terminada la fase.

Evidencia: **12 pruebas nuevas de navegador**, incluidas nueve comparaciones
de carga/error/error común a 1450/900/390 px. Las otras cubren respuestas
superadas (éxito/error), compatibilidad pendiente, contenedor desconectado y
texto seguro. **23 aprobadas** de entrada/sesión y **68 de regresión** de
navegación, pestañas, Cliente/Acciones y soporte. Total **103 distintas**;
la comprobación final repite entrada junto con las 12 nuevas (22 aprobadas).
Once Node contrastan clasificación con las funciones originales, metadata y
prioridad de ruta. Suite completa **368 aprobadas y tres fallos anteriores**
(`cost_sprint_details`, `executive_report`, `financial`). El extractor de
`legacy_tools.test.cjs` admite el argumento de compatibilidad nuevo; conserva
todas sus comprobaciones. Ruff/formato, Django y diff aprobados. Capturas en
`tmp/migration/project_detail/loading/`, inspeccionadas escritorio/móvil.
Sin cambios de API/cálculos, proveedores simulados, sin correos reales ni push.

### Inicialización y sesión AER/IXS (selección de estado separada)

`project_session{,_model,_view}.js` separa los inicializadores AER/IXS, apertura
de IA IXS y enlace Cliente/Acciones. Conserva la identidad del estado al volver
al mismo proyecto y sus reinicios originales al cambiar de ID; Clockify vuelve
a la semana local. IA IXS conserva el orden vista/fuentes/historial/Drive.
Cliente/Acciones reutiliza su caché y modifica solo los campos AER compartidos;
su respuesta no se aplica si el contenedor cambió de familia.

El histórico diferido usa la API existente, conserva la comprobación de identidad
del proyecto y actualiza el Gantt modular Ejecutivo/Planeación. Los errores de
entrada y el aviso de backend AER mantienen texto, cajas y estilos mediante DOM
seguro. `main.js` registra la sesión antes de cargar el archivo anterior.

**Fase 10 parcial.** `projectSessionContext` conserva los adaptadores a globals;
no se extrajo todavía su almacenamiento ni toda la entrada común. Siguiente:
estado/contextos/entrada y auxiliares de Planeación/soporte. Mantener puentes y
comparación, sin retirar script/shim ni reabrir pestañas ya migradas.

Evidencia inicial: **13 pruebas nuevas de navegador**, con nueve comparaciones
a 1450/900/390 px de errores/aviso, conservación/reinicio y apertura IA/cache.
**25 de entrada/transporte Cliente/Acciones aprobadas**. Siete Node contrastan
estados iniciales con el código anterior y verifican selección/semana/diagnóstico;
suite completa **357 aprobadas y tres fallos anteriores** (`cost_sprint_details`,
`executive_report`, `financial`). Capturas en
`tmp/migration/project_detail/session/`, inspeccionadas escritorio/móvil.
Ruff/formato, Django y diff aprobados. Proveedores simulados, sin correos reales,
sin cambios en API/cálculos y sin push. Regresión adicional: **80 aprobadas**
de refresco/navegación, IA AER/IXS, histórico/respuesta tardía y soporte.
Total de este bloque: **118 de navegador/soporte aprobadas**, sin duplicados.

### Montaje de pestañas AER/IXS (controlador compartido separado)

`project_tabs.js` decide qué módulo presenta cada pestaña en ambas familias.
Conserva la evaluación diferida de contextos AER, el montaje Cliente/Acciones
en el contenedor IXS y su sincronización de pestaña, estados de Planeación/Azure,
callbacks de edición y comprobaciones de proyecto/pestaña. Recursos se precarga
antes de Ejecutivo/Esfuerzo IXS, como antes. La entrada registra este controlador
después de las vistas y antes de cargar el puente anterior.

El respaldo AER usa el renderer modular ejecutivo sin añadir el aviso reservado
a la pestaña ejecutiva normal. `project_tabs_view.js` conserva el respaldo IXS
con DOM seguro y eventos externos; el botón de compatibilidad todavía conserva
su callback a la vista anterior. Las rutas normales no ejecutan las ramas de
montaje/renderizado anteriores; sus funciones globales solo delegan.

**Montaje separado; fase 10 parcial.** `projectTabsContext` conserva getters y
callbacks a los globals. Inicializadores `renderDashboard…`, estado/cachés,
apertura de IA IXS y enlace Cliente/Acciones todavía requieren extracción junto
con los auxiliares de Planeación/soporte. Siguiente: inicialización/estado;
no repetir las vistas ni dar por retirada la dependencia del script/shim.

Evidencia: **ocho pruebas nuevas de navegador aprobadas**, incluidas seis
comparaciones de respaldos a 1450/900/390 px, recorrido de las 18 pestañas y
montaje con renderizado HTML anterior bloqueado. **25 de entrada/transporte
Cliente/Acciones aprobadas**. Veintiuna Node prueban contextos diferidos,
argumentos/estados, lifecycle y selección de módulos; suite completa **350
aprobadas y tres fallos anteriores** (`cost_sprint_details`, `executive_report`,
`financial`). Ruff/formato, Django y diff aprobados. Capturas en
`tmp/migration/project_detail/tabs/`. Sin API nueva ni cálculos modificados;
no se repitieron pruebas de backend. Datos/proveedores simulados, sin consultas
ni correos reales. Cambios ajenos intactos; sin push.

Regresión: **63 aprobadas** de Ejecutivos, IA AER y montaje real/lecturas/
edición de Planeación, Esfuerzo, Riesgos/RAID, Recursos, Acciones, Azure,
IA IXS y Comunicación, más soporte. Junto con ocho nuevas y 25 de entrada/
Cliente/Acciones: **96 de navegador/soporte aprobadas**. Respaldos inspeccionados
en escritorio/móvil.

### Encabezados, navegación y refresco AER/IXS (bloque anterior)

`project_shell_model.js` conserva categoría del estado AER y etapa actual IXS,
reutilizando fases/fechas del modelo existente. `project_shell_view.js` crea
los encabezados y sus ocho/diez pestañas con DOM seguro y eventos externos;
mismos iconos SVG, etiquetas, metadatos, clases y estilos externos.
Se conservan fechas y texto de etapas con la misma presentación anterior.

`project_shell.js` controla navegación y refresco por API v1 existente.
Mantiene el alias AER minutas→IA y el orden de sus cinco cargas al entrar a IA;
Acciones conserva su carga de pendientes. AER restaura la pestaña capturada al
actualizar. IXS conserva la invalidación de Cliente/Acciones y vuelve a Ejecutivo,
con la inicialización anterior. Respuestas superadas o de otra carga/familia
se descartan. Se conserva la presentación de error anterior de cada familia.

**Encabezados/navegación/refresco separados; fase 10 parcial.** Los contextos,
entrada/estado, `renderDashboard…` y dispatch/montaje de pestañas siguen como
puentes en el archivo anterior. Siguiente: extraer esos bloques y los auxiliares
compartidos, incluido soporte/error. No retirar todavía script/shim; no activar
ACCESS_ENFORCED ni modificar Horas por mes, cálculos o regreso al origen.

Evidencia: **34 pruebas de navegador aprobadas por bloques** (24 comparaciones
a 1450/900/390 px: datos completos, vacíos, texto especial y cerrado para ambas
familias). Recorrido de todas las pestañas, alias/cargas, refresco y navegación
de regreso, error e ignorar respuestas superadas/de otra familia probados.
Diez pruebas de entrada aprobadas. Nueve Node del modelo contrastan etapa/
estado con el original; suite completa **329 aprobadas y tres fallos anteriores**
(`cost_sprint_details`, `executive_report`, `financial`). Ruff/formato, Django
y diff aprobados. Capturas en `tmp/migration/project_detail/shell/`.
Sin cambios de API; no se repitieron sus pruebas. Datos/proveedores simulados,
sin correos ni consultas reales. Cambios ajenos intactos; sin push.

Regresión: **65 aprobadas** (Ejecutivos AER/IXS, fuentes IA AER,
Cliente/Acciones IXS y soporte). Con diez de entrada y 34 del bloque:
**109 de navegador/soporte aprobadas**. Capturas inspeccionadas escritorio/móvil.

### IA AER/T&M: acciones por API (pestaña completa, bloque anterior)

`project_aer_ai.py` conserva seis GET de fuentes (se añade el prompt por
defecto) y ocho POST explícitos: `analizar`, `generar-resumen`, `preguntar`,
`correo`, `minuta-borrador`, `minuta-drive`, `minuta-guardar`, `config-guardar`.
Mismas funciones de `ai_functions.py`, argumentos, tipos, proveedores y errores
públicos. El proyecto procede de la ruta; generación/guardado exige
`edit_operations`, configuración `manage_integrations`, alcance total y CSRF.
No se llama al modelo por abrir la pestaña ni se reintentan escrituras solas.

`aer_ai_actions.js` controla análisis, resumen, preguntas y correo;
`aer_ai_minutes_actions.js` separa borradores con/sin Drive, guardado, configuración,
prompt predeterminado y copiado. `aer_ai_actions_model.js` conserva preguntas de
resumen y selección de cinco archivos. Mantiene validaciones, textos completos,
borradores editables, mensajes de coste/caché/persistencia y recarga de minutas.
Respuestas de otro estado/proyecto no se aplican; resultados de un formulario
cerrado no reemplazan el nuevo. Una respuesta normal no borra la siguiente
pregunta que ya se esté escribiendo. Los puentes solo delegan; no se ejecutan
las acciones ni escrituras RPC anteriores en esta pestaña.

**IA AER completa; fase 10 parcial.** Quedan encabezados, pestañas, entrada/
estado y auxiliares comunes del detalle. Mantener script/shim hasta completar
su integración; limpieza/CSP pertenecen a fase 11. Hallazgo preservado: el
manejador común `showError` reemplaza el contenido del dashboard en algunos
errores; no se cambió su comportamiento durante esta migración.

Evidencia: **102 API aprobadas** (57 de acciones y 45 de lecturas): firmas,
permisos/alcance antes de construir proveedores, CSRF, cuerpo objeto, rutas y
errores públicos. **29 casos de navegador aprobados por bloques**, incluidos
18 comparaciones de resultados generados a 1450/900/390 px; se conserva toda
la evidencia de pantalla/formularios anterior. Se prueban validación, copia,
pregunta frente a resumen, edición/guardado, búsqueda posterior, errores y
reintento, duplicados y respuestas tardías sin perder notas nuevas.
Siete Node del modelo y quince del cliente aprobadas; suite completa **320
aprobadas y tres fallos anteriores** (`cost_sprint_details`, `executive_report`,
`financial`). Ruff/formato, mypy del API nuevo, Django y diff aprobados.
Capturas en `tmp/migration/project_detail/aer_ai_view/actions/`, inspeccionadas
escritorio/móvil. Pruebas con proveedores simulados, sin Claude/Drive/Sheets
reales ni correos enviados. Sin cambios de cálculos ni ACCESS_ENFORCED; sin push.

Regresión: **75 de navegador/soporte aprobadas** (fuentes y vista/formularios
IA AER, entrada, Ejecutivo AER y soporte). Con los 29 casos de acciones:
**104 de navegador/soporte**; sumadas las 102 API, **206 aprobadas**.

### IA AER/T&M: presentación y formularios (bloque anterior, parcial)

`aer_ai_presentation_model.js` conserva los datos derivados de la pantalla,
fecha de memoria, extracto de la última minuta y formato mínimo del resumen.
`aer_ai_dom.js` presenta ese formato con nodos de texto/strong/br sin insertar
HTML. `aer_ai_view.js` monta toda la pestaña y `aer_ai_documents_view.js` separa
historial y documentos. Mantiene el contenido y los estilos/cajas originales.

`aer_ai_forms_view.js` presenta lectura de minuta, resumen ejecutivo, correo,
generación de minuta, configuración y borrador editable. DOM seguro/eventos
externos, mismos IDs, valores y estilos. El prompt mantiene asignación por
propiedad `value`, como el formulario anterior. Enlaces de documentos solo
aceptan HTTP(S); cadenas de etiquetas siguen siendo texto.

`aer_ai_presentation.js` controla historial, ocultar/documentos, selección
máxima de cinco, preguntas sugeridas, lectura y apertura de formularios. Las
recomendaciones reutilizan el editor modular de Acciones. El montaje no
ejecuta `aerIAVista`, sus auxiliares de presentación ni `_aerModal`; el borrador
devuelto por la acción anterior también se pinta con el módulo nuevo.

**IA AER y fase 10 siguen parciales:** las acciones de generación/guardado,
validación y copiado todavía delegan a sus funciones anteriores; varias usan
RPC. Siguiente: API/controlador para análisis, preguntas, correo, resumen,
minutas y configuración, con sus permisos originales. Después estructura,
estado y auxiliares compartidos. No retirar script/shim ni activar accesos.

Evidencia: **29 casos de navegador aprobados por bloques**, incluidos 27
comparaciones a 1450/900/390 px: pantalla rica/carga/oculta y seis formularios.
También se conserva la comparación de fuentes (12 aprobadas, nueve visuales).
Se prueban límite de selección, teclado/foco, historial, texto seguro y montaje
con renderizadores anteriores sustituidos por errores. Veinte Node del modelo
contrastan formato/extracto/presentación con el original; suite completa:
**312 aprobadas y los tres fallos anteriores** (`cost_sprint_details`,
`executive_report`, `financial`). Ruff/formato, Django y diff aprobados.
Capturas en `tmp/migration/project_detail/aer_ai_view/`; inspeccionadas pantalla
y formulario en escritorio/móvil. Datos simulados, sin Claude/Drive/Sheets ni
correos reales. Sin cambios de API/cálculos; no se repitieron sus pruebas.

Regresión: **34 aprobadas** de entrada, Ejecutivo AER y soporte del frontend.
Con los 29 casos nuevos y doce de fuentes: **75 casos aprobados**.

### IA AER/T&M: lecturas, contexto/hechos y estilos (bloque anterior, parcial)

`project_aer_ai.py` expone cinco GET explícitos
`screens/proyectos/<id>/ia-aer/{analisis,resumen,minutas,config,archivos}/`.
Reutiliza las funciones de `ai_functions.py`, contexto/proveedores y errores
originales. `view_operations` y alcance total; configuración conserva
`manage_integrations`. Contexto del análisis guardado en query JSON validado;
el proyecto autorizado lo determina la ruta. No genera análisis al abrir.

`aer_ai_sources.js` controla carga y caché de análisis/resumen guardados,
minutas, configuración y búsqueda Drive. Conserva restauración y consulta bajo
demanda, avisos, reintentos y búsqueda automática solo con carpeta/nombre
configurados. No sustituye un análisis recién generado por uno guardado.
Respuestas de otro proyecto/estado se descartan; refrescar el dashboard del
mismo proyecto conserva la carga y evita dejar los indicadores bloqueados.

`aer_ai_model.js` separa contexto y hechos/alertas con las reglas originales:
28 compromisos en el contexto; ocupación sobre toda la planeación, estados
excluidos, vacaciones aprobadas, fechas/ventana de 30 días y umbral de 6 puntos.
No cambia los cálculos ni el texto enviado por las acciones anteriores.
`project_detail_aer_ai.css` conserva el CSS principal inyectado; su link con el
ID original evita reinyección en la ruta nueva. La anterior sigue inyectándolo.

**IA AER y fase 10 parciales.** La vista `aerIAVista`, auxiliares de presentación,
formularios y acciones (análisis/preguntas/correo/resumen/minutas/configuración)
todavía viven en el JS anterior y varias usan RPC. Siguiente bloque: vista y
acciones de IA AER. No retirar script/shim ni marcar la pestaña completa.

Evidencia: **38 API aprobadas**; permisos/alcance antes de fuentes, contexto
válido/inválido, firmas y errores públicos. Seis Node contrastan contexto/hechos
contra el original; nueve del controlador verifican caché, estados, Drive,
reintento y respuestas tardías; catorce del cliente aprobadas. Suite completa:
**292 aprobadas y los tres fallos anteriores** (`cost_sprint_details`,
`executive_report`, `financial`). Nueve comparaciones de estilos/cajas a
1450/900/390 px (vacío, memoria guardada y Drive configurado), con capturas
en `tmp/migration/project_detail/aer_ai_sources/`, inspeccionadas escritorio/móvil.
Ruff/formato, mypy del API nuevo y Django aprobados. Proveedores simulados;
sin consultas reales a Claude, Drive, Sheets ni correos enviados. Sin push.

Navegador/soporte: **46 aprobadas**, incluidas doce de IA AER, entrada del
proyecto, Ejecutivo AER y soporte. Caché, ausencia de generación al entrar,
reintento, estado reemplazado y refresco del mismo proyecto probados. Con las
38 API: **84 pruebas aprobadas**. Diff sin incidencias.

### Recursos AER/T&M (pestaña completa)

`aer_resources_model.js` conserva selección inicial, agrupación por persona,
última evaluación, indicadores, categorías, orden de fechas, curva y distribución.
`aer_resources_view.js` presenta resumen, gráfica, comentarios, tablas y editor
con DOM seguro, SVG y eventos externos; reutiliza el CSS AER ya externo.
`aer_resources.js` coordina selección y operaciones; no ejecuta `_aerVistaRecursos`,
`_aerEvalCategoria`, `_aerEvalClase` ni el formulario HTML anterior.

La lectura de evaluaciones sigue en el dashboard AER existente por API v1.
`project_aer_resources.py` añade POST explícitos a
`screens/proyectos/<id>/evaluaciones-aer/guardar/` y `eliminar/`: mismos servicios
y argumentos de `guardarEvaluacionAER` y `eliminarEvaluacionAER`, ID de la ruta,
`edit_operations`, alcance total y CSRF antes de consultar fuentes. Mantiene
valores numéricos como texto en el envío, validación y cálculo del servicio.

Se conservan las últimas cinco evaluaciones **del proyecto**, no solo de la
persona seleccionada; el selector cambia únicamente su resumen. La próxima
evaluación se elige de todo el histórico, incluso si es una fecha pasada, igual
que antes. Guardar selecciona el recurso guardado; borrar usa el resumen devuelto.
Errores permiten reintentar sin perder borrador; respuestas de otro dashboard no
se aplican ni cierran un editor abierto posteriormente.

**Recursos AER completo; fase 10 parcial.** Siguiente: IA AER, luego estructura,
estado y auxiliares compartidos. Mantener script/shim y comparación anterior;
limpieza/CSP en fase 11. ACCESS_ENFORCED y Horas por mes sin cambios.

Evidencia: **15 API, 11 de soporte y 18 de navegador aprobadas**. Quince
comparaciones a 1450/900/390 px de datos completos/vacíos, selección y formularios
de alta/edición. Guardado/borrado, confirmación, reintento, selección tras guardar,
texto seguro y respuestas tardías probados. Diecisiete Node contrastan el modelo
con el original; trece del cliente aprobadas. Suite completa: **276 aprobadas y
los tres fallos anteriores** (`cost_sprint_details`, `executive_report`,
`financial`). Ruff/formato, mypy del API nuevo, Django y diff aprobados.
Capturas en `tmp/migration/project_detail/aer_resources/`, inspeccionadas en
escritorio y móvil. Datos/proveedores simulados, sin correos reales. Sin push.

Regresión: **46 de navegador aprobadas** (entrada del proyecto, Ejecutivo AER
y Riesgos AER). Junto a las nuevas y soporte: **90 pruebas aprobadas**.

### Riesgos AER/T&M (pestaña completa)

`aer_risks_model.js` conserva agrupación, clasificación, matriz, exposición,
atención y porcentajes de presentación. `aer_risks_view.js` presenta indicadores,
riesgos priorizados, distribución, matriz, seguimiento y editor con DOM seguro
y eventos externos. `aer_risks.js` controla las operaciones y descarta respuestas
de otra carga del proyecto; una respuesta no cierra un editor abierto después.
El montaje no ejecuta `_aerVistaRiesgos`, `_aerTablaAcciones` ni `_aerModal`.
«Nueva acción» reutiliza el editor modular de Acciones y su API existente.

`project_aer_risks.py` expone GET `screens/proyectos/<id>/riesgos-aer/` y POST
explícitos `guardar/`, `eliminar/`, `limpiar-duplicados/`, con las mismas firmas y
servicios del RPC anterior. Lecturas con `view_operations`, escrituras con
`edit_operations`, alcance total y CSRF antes de consultar las fuentes.
Se conserva el borrado por UID y la recarga posterior. No se añade botón de
limpieza: antes solo existía el auxiliar invocable, que ahora delega a la API.

**Hallazgo anterior preservado:** la agrupación visual por título conserva la
primera fila cuando ese título tiene responsables/fechas distintos. No se cambia
para evitar alterar los resultados. Tampoco se recalculan los indicadores del
dashboard tras guardar, ni se repinta inmediatamente Riesgos al guardar una
acción desde su editor compartido: se conserva la actualización anterior.

**Riesgos AER completo; fase 10 parcial.** Siguiente: Recursos AER, luego IA y
estructura/estado/auxiliares compartidos. No retirar script/shim; limpieza y CSP
en fase 11. Horas por mes y ACCESS_ENFORCED sin cambios.

Evidencia: **28 API y 23 de navegador aprobadas**. Dieciocho comparaciones a
1450/900/390 px: datos completos, vacíos y duplicados; alta/edición, incluido
impacto sin opción coincidente. CRUD, confirmación, reintento sin perder borrador,
limpieza, acción compartida, texto seguro y respuestas tardías probados.
Además, **48 de regresión/soporte aprobadas**: entrada del proyecto, Ejecutivo
AER, transporte de Acciones y soporte del frontend (**99 total**).
Capturas en `tmp/migration/project_detail/aer_risks/`, inspeccionadas en escritorio
y móvil. Nueve Node contrastan el modelo con funciones originales; doce del
cliente de datos aprobadas. Suite completa: **258 aprobadas y los tres fallos
anteriores** (`cost_sprint_details`, `executive_report`, `financial`).
Ruff/formato, mypy del API nuevo, Django y diff aprobados. Datos/proveedores
simulados; sin correos reales. No se ha hecho push.

### Esfuerzo AER/T&M (pestaña completa)

`aer_effort_model.js`, `aer_effort_view.js` y `aer_effort.js` separan indicadores,
distribución/tendencia/dona, consumo por recurso, filtro de registros y ventana
«Ver más», con DOM seguro y eventos externos. El montaje no ejecuta
`_aerVistaEsfuerzo` ni la ventana HTML anterior. Semana inicial y vista previa de
cinco filas, top de actividades/recursos y formatos se conservan.

`GET screens/proyectos/<id>/aer/registros/?desde=...&hasta=...` usa el mismo
`dashboard.entries_in_range`, store y proveedor de horas del RPC anterior.
Lectura con `view_operations` y alcance total, antes de consultar fuentes.
Conserva validación, deduplicación y límite del servicio. El rango solo afecta
a los registros; los indicadores/gráficas/consumo siguen del proyecto completo.
Las respuestas anteriores a otra consulta o carga del proyecto no se aplican.

**Esfuerzo AER completo; fase 10 parcial.** Quedan Riesgos, Recursos e IA AER y
estructura/estado/auxiliares compartidos. Mantener script/shim y comparación;
limpieza/CSP en fase 11. No activar ACCESS_ENFORCED ni modificar Horas por mes.

Evidencia: **75 API y 67 de navegador/soporte aprobadas** (142 total); las 67
incluyen 19 de Esfuerzo y regresión de entrada, Ejecutivo AER, Acciones y soporte.
Quince comparaciones de pantalla/ventana a 1450/900/390 px. Probados permiso y
alcance, argumentos del proveedor, rango, vista previa/ventana completa, reintento,
texto seguro y respuestas anteriores de otra consulta/proyecto que no se aplican.
Trece Node del modelo contrastan reglas con el original y once del cliente de
datos aprobadas; suite completa: 248 aprobadas y tres fallos anteriores.
Ruff/formato, mypy de project_detail, Django y diff aprobados. Capturas en
`tmp/migration/project_detail/aer_effort/`; inspeccionadas en escritorio y móvil.
Datos/proveedores simulados, sin correos reales.

### Planeación AER/T&M: filtros, selección y rango (pestaña completa)

`aer_planning_controls.js` gestiona búsqueda/filtros, selección e inicialización/
cambio de rango; `aer_planning_filters_model.js` conserva coincidencias, opciones
y valores iniciales. `aer_planning_filter_view.js` construye los seis menús con
DOM seguro/eventos externos y cierre al pulsar fuera. Se preservan búsqueda sin
acentos, fechas inclusivas, selección visible/oculta y estados de los controles.
Los puentes globales solo enlazan estado/ciclo de vida compartidos y delegan;
los controles nuevos no llaman a los auxiliares anteriores.

**Planeación AER completa; fase 10 parcial.** Quedan Esfuerzo, Riesgos, Recursos e
IA AER, encabezados/navegación/estado y auxiliares compartidos. Mantener script y
shim hasta completar esos bloques. Limpieza/CSP en fase 11; no activar permisos.

Evidencia: **74 pruebas de Planeación y 48 de regresión aprobadas** (122 total).
Se incluyen 57 comparaciones de Planeación a 1450/900/390 px; 18 son de los seis
menús de filtros. Probados fechas/búsqueda, teclado/foco, cierre al pulsar fuera,
selección visible/oculta, indeterminate, texto seguro y protección ante otro
dashboard; se sustituyen todos los auxiliares anteriores de controles por errores.
Trece Node nuevas contrastan filtros/rango con el original. Suite completa:
234 aprobadas y los tres fallos anteriores. Ruff/formato, Django y diff aprobados.
Sin cambios de backend; no se repitieron las API del bloque anterior. Capturas en
`tmp/migration/project_detail/aer_planning_controls/` y las carpetas anteriores;
inspeccionadas en escritorio/móvil. Proveedores simulados y sin correos reales.

### Planeación AER/T&M: vista principal e indicadores (bloque anterior parcial)

Modelo de indicadores, agrupaciones/estados/posiciones de Gantt, atención,
ocupación y vacaciones en `aer_planning_model.js`, sin cambiar resultados.
`aer_planning_view.js`, `aer_planning_timeline.js`, `aer_planning_tables.js`
y los auxiliares DOM de la página presentan la pestaña completa con eventos
externos. La ruta activa monta estos módulos; no ejecuta `_aerVistaPlaneacion`.
Se reutilizan formularios/API existentes y el botón Comunicados de Roadmap.

**Planeación AER aún parcial:** filtros de cabecera/búsqueda, selección y estado
del rango delegan a auxiliares anteriores. El popup de filtros sigue anterior.
Siguiente separar esos controles. Fase 10 parcial; no retirar script/shim.

Hallazgo conservado: el título del bloqueo crítico usa `x.label` en el original,
aunque el grupo contiene `dependencia`. Puede quedar vacío; no se corrigió dentro
de la migración para conservar los datos y la presentación anterior.

Evidencia: **52 pruebas de Planeación y 48 de regresión aprobadas** (entrada,
Ejecutivo AER, Acciones y soporte); 39 comparaciones de Planeación a
1450/900/390 px, incluidos alertas, vacaciones, rangos invertidos y filtros activos.
Se comprueban interacción, guardados, texto/UID seguros y montaje sin ejecutar
renderizadores anteriores. Veintiuna Node del modelo aprobadas; nueve contrastan
el resumen y funciones de fechas/estados/posición con el original. Suite Node
completa: 221 aprobadas y tres fallos anteriores. Ruff/formato, Django y diff
aprobados. Sin cambios de backend ni repetición de API. Capturas en
`tmp/migration/project_detail/aer_planning_view/`, además de formularios/transporte;
inspeccionadas en escritorio y móvil con proveedores simulados.

### Planeación AER/T&M: formularios y modelo de capacidad/importación (bloque anterior parcial)

`aer_planning_forms.js` presenta altas/ediciones de actividades/hitos y vacaciones,
avisos de capacidad y carga/preview de CSV/TSV con DOM seguro y eventos externos.
`aer_planning.js` los conecta a las operaciones API existentes. La ruta nueva
no llama a `_aerModal` ni a los constructores anteriores de esos formularios.

`aer_planning_model.js` conserva recursos del proyecto, consumo de capacidad,
ocupación actual, máximo de capacidad en un rango y parser/fechas de importación.
Se contrasta con las funciones originales, incluidos proyectos vacíos, tareas
vencidas que siguen abiertas, tareas futuras, hitos, cierres, omisiones de filas
y las limitaciones existentes al separar texto por espacios. No cambia fórmulas.
Los wrappers compartidos delegan al modelo; los formularios/guardados lo usan
directamente. La comparación anterior mantiene las funciones originales.

**Planeación AER y fase 10 siguen parciales:** faltan modelo de indicadores y
fechas del Gantt, vista principal, filtros y selección de tabla. No retirar
fallback/shim ni activar ACCESS_ENFORCED. Después las otras cuatro pestañas AER
y estructura compartida; limpieza/CSP en fase 11.

Evidencia: **40 pruebas de Planeación y 48 de regresión aprobadas**, con 30
comparaciones de pantalla/formularios a 1450/900/390 px (incluyen valores y
estado habilitado de campos). Capacidad, estados/cierre, dependencias, CSV/TSV
desde archivo, teclado, texto seguro y reintento/guardados probados. La ruta
nueva se prueba con los formularios/helpers anteriores sustituidos por errores.
Doce Node contrastan modelo con el original; diez del cliente de datos aprobadas.
Suite Node completa: 212 aprobadas y tres fallos anteriores. Ruff/formato,
Django y diff aprobados. Sin cambios de backend; no se repitieron las 49 API
del bloque anterior. Capturas en
`tmp/migration/project_detail/aer_planning_forms/` y `aer_planning_transport/`;
revisadas en escritorio y móvil, con datos y proveedores simulados.

### Planeación AER/T&M: operaciones y transporte (bloque anterior parcial)

`project_aer_planning.py` expone ocho POST de guardar, importar, estado,
cerrar, eliminar, eliminar-lote y guardar/eliminar vacaciones. Reutiliza las
funciones de `apps.aer.rpc.FUNCTIONS` y sus servicios, con `edit_operations`,
alcance total, CSRF y el proyecto de la ruta cuando la firma recibe proyecto.
El borrado individual conserva la firma original por UID.

`sections/aer_planning.js` separa las operaciones de sus formularios existentes;
`data.js` conserva timeout y usa el cliente de datos compartido. Los puentes
anteriores delegan en la ruta nueva. Se mantienen confirmación de
sobreasignación, fechas de cierre, guardado ligero, importación, confirmación
física del borrado por lote y recarga solo en los mismos flujos. Respuestas
de otro dashboard no se aplican ni cierran un editor abierto después.

El borrado individual anterior recarga aun con `{ok:false}` si la solicitud
responde sin fallo de transporte; se conserva ese comportamiento en este bloque
y se prueba expresamente. Cualquier corrección de negocio requiere otro alcance.

**Planeación AER y fase 10 siguen parciales:** faltan modelo/presentación,
formularios, filtros, parser y cálculos de capacidad. Mantener fallback/shim;
no activar ACCESS_ENFORCED ni alterar Horas por mes.

Evidencia: **109 aprobadas** (49 API, 25 e2e de Planeación más soporte y regresión
de entrada/Acciones); 18 comparaciones de pantalla completa/vacía y formularios
a 1450/900/390 px. Cubren guardado/reintento, confirmación de sobreasignación,
estado/cierre, vacaciones, importación, borrado físico por lote, borrado simple
y respuestas tardías. Diez Node del cliente de datos aprobadas; suite completa
200 aprobadas y los tres fallos anteriores. Ruff/formato, mypy nuevo, Django
y diff aprobados. Capturas en
`tmp/migration/project_detail/aer_planning_transport/`; revisada la de escritorio.
Proveedores simulados, sin consultas reales ni correos enviados.

### Acciones AER/T&M e IXB/SaaS/RaaS: vista y formularios

`actions_view.js` monta las dos tablas, indicadores, seguimiento, búsqueda y
formularios de alta/edición de acciones y pendientes Beecker/Cliente con DOM
seguro y eventos externos. `actions.js` los conecta al modelo/API ya separados.
La ruta activa no llama a `_aerVistaAcciones`, `aerIAAccionesPartesVista` ni
`_aerModal` para esta pestaña; mantiene los puentes de entrada/estado y el
fallback de comparación. La IA de AER todavía conserva su propia vista anterior.

Sin cambios de negocio: se conserva incluso el comportamiento anterior de
«Filtros» (abre el alta) y «Ver todas las acciones» (limpia duplicados), así como
el campo «Próxima revisión» de la tabla principal que guarda `fechaReal`.
Si se desea corregir esos comportamientos, hacerlo aparte de la migración.

Evidencia: **184 aprobadas** (99 API y 85 e2e), nueve variantes del Ejecutivo
sin cambios deseleccionadas. Se incluyen 42 comparaciones de vista/formularios
AER/IXS a 1450/900/390 px; búsqueda, edición/guardado/borrado, reintento,
respuestas tardías, texto seguro y teclado. Capturas en
`tmp/migration/project_detail/actions_transport/` y `actions_forms/`; revisadas
en escritorio y móvil. Dieciocho Node dirigidas aprobadas; suite completa
199 aprobadas y los tres fallos anteriores. Ruff/formato, Django y diff sin
incidencias; proveedores simulados. **Acciones completa; fase 10 parcial.**

### Revisión de avances de Claude y operaciones de Acciones AER/IXS (bloque anterior)

Revisados commits, API y delegaciones activas: Cliente de ambas familias y
Centro de Comunicación IXS sí usan módulos nuevos. Se corrigió el inventario
superior que aún los marcaba pendientes. Comprobación propia: 94 e2e, 26 API,
siete Node y mypy de Cliente/detalle aprobados; los seis errores antiguos ya
están corregidos. Esta es una revisión dirigida, no una repetición de las
1437 pruebas históricas reportadas por Claude.

Nuevo bloque parcial de Acciones: `project_actions.py` expone dos lecturas
y siete mutaciones para ambas familias con servicios/argumentos originales,
permisos de lectura/edición, alcance total y CSRF. `actions_model.js` separa
el resumen; `actions.js` hace los guardados, edición directa, confirmaciones,
recarga tras eliminar y pendientes Beecker/Cliente por API. Conserva caché y
borradores al reintentar; respuestas antiguas no cierran otro editor.

Evidencia: 152 aprobadas de API/navegador/soporte (99 API, 14 e2e del bloque,
entrada y regresión Cliente/Comunicación). Seis comparaciones AER/IXS a
1450/900/390 px en `tmp/migration/project_detail/actions_transport/`.
Doce Node dirigidas; Node completo 198 aprobadas y los tres fallos previos.
Ruff/formato, mypy nuevo, Django y diff aprobados. Diecisiete e2e adicionales
de navegación AER/Acciones aprobaron tras adaptar el fixture de lectura por API;
inspeccionada la captura de IXB en escritorio. Fuentes simuladas y sin correos reales.

**En ese bloque Acciones y fase 10 seguían parciales:** faltaba separar su
vista, filtro de tabla y ambos formularios, que seguían en el script anterior
con eventos en línea. Después pestañas AER y estructura compartida. No retirar el shim ni
activar ACCESS_ENFORCED; limpieza/CSP pertenecen a fase 11.

### Fase 10: carga de Cliente/Acciones IXB (parcial)

`ixs_client_actions.js` sustituye la lectura RPC por la API `cliente/` existente.
Conserva caché compartida, mensajes, ID validado y metadatos del proyecto;
descarta respuestas tardías. El renderer, filtros/exportaciones y editores
compartidos con AER siguen anteriores; **ambas pestañas siguen parciales**.
Sin nuevos servicios/endpoints ni cambios de cálculos/permisos.

Evidencia: **81 aprobadas** (15 e2e del bloque, 43 API, 10 entrada, 11 soporte,
dos flujos IA). Incluye 12 comparaciones llena/vacía a 1450/900/390 px,
caché, reintento, ID inválido y salida durante carga. Cinco Node aprobadas.
Ruff/formato y diff aprobados. Capturas en
`tmp/migration/project_detail/ixs_client_actions/`; inspeccionada Cliente en
escritorio. Fuentes simuladas. Siguiente modelo/vista/editores compartidos.

### Fase 10: IA IXB/SaaS/RaaS completa

Vista y eventos en `ixs_ai_view.js`; ventanas y acciones en
`ixs_ai_controller.js`. Reutiliza modelo/paneles separados y CSS externos.
Incluye indicadores, evidencias, recomendaciones/acción/RAID, preguntas,
análisis, memoria, reportes/comunicados, historial/minutas y Drive. No ejecuta
los renderizadores/formularios anteriores en la ruta nueva. Mantiene wrappers
de estado/entrada y código de comparación, necesarios mientras el detalle
completo sigue parcial.

Nueve POST explícitos conservan servicios/argumentos, capacidades y alcance
total originales, con CSRF. Se mantiene revisión de borradores, prompts,
límites, fuentes y cálculos. Respuestas de ventanas cerradas no contaminan
otra ventana. Sin consultas reales a modelos, Drive, Azure ni Gmail en pruebas.

Evidencia: **185 aprobadas** (106 API, 58 e2e IA, 10 entrada, 11 soporte),
incluidas 18 comparaciones de pantalla y 27 de ventanas a 1450/900/390 px,
guardados/reintentos, texto seguro, filtros y límite de transcripciones.
Capturas en `tmp/migration/project_detail/ixs_ai_full/` y `ixs_ai_sources/`;
inspeccionada rica de escritorio. Node: 181 aprobadas, tres fallos anteriores;
17 dirigidas aprobadas. Ruff/formato, Django y diff aprobados. Mypy conserva
seis errores previos en otros archivos. **IA completa, fase 10 parcial.**

### Fase 10: paneles de capacidad y cambios de IA (parcial)

`ixs_ai_panels_view.js` separa ambos paneles con DOM seguro e iconos originales.
Reutiliza el modelo de IA, sin cambiar cálculos ni presentación. Ver recursos
usa evento externo y conserva navegación. La extensión de la ruta nueva delega;
la comparación sigue ejecutando los paneles anteriores.

Evidencia: 32 pruebas navegador/soporte aprobadas, incluidas 15 comparaciones
de cinco variantes a 1450/900/390 px, texto seguro, delegación y navegación.
16 pruebas Node dirigidas aprobadas. Ruff/formato y diff aprobados.
Capturas en `tmp/migration/project_detail/ixs_ai_sources/`; inspeccionada
`comparable/1450/new.png`. Fuentes simuladas, sin llamadas reales a IA.

**IA y fase 10 parciales:** el resto de vista/eventos y las acciones/formularios
permanecen anteriores. No retirar shim ni script anterior.

### Fase 10: modelo de IA IXB (parcial)

Contexto, snapshot, cambios entre cortes y capacidad por recurso separados en
`ixs_ai_model.js`, con dependencias explícitas y sin red/DOM. Las funciones
anteriores delegan solo en la ruta nueva; comparación conserva las originales.
No se cambiaron fórmulas, redondeos ni límites. Se conserva la diferencia
anterior entre horas del contexto (sin negativos, por personas con nombre) y
snapshot (suma de duraciones numéricas), documentada en el traspaso.

Evidencia: cuatro pruebas Node nuevas contra las funciones originales; 16
aprobadas en la suite dirigida. 35 pruebas navegador/soporte aprobadas: nueve
comparaciones completa/vacía/parcial a 1450/900/390 px, entrada, soporte,
reintentos/cargas y comprobación de delegación real con resultados idénticos.
Capturas regeneradas en `tmp/migration/project_detail/ixs_ai_sources/` e
inspeccionada escritorio. Ruff/formato y diff aprobados. Fuentes simuladas.

**IA sigue parcial:** falta separar vista/eventos y migrar las acciones y
formularios a API. Fase 10 no terminada; mantener shim y script anterior.

### Fase 10: fuentes e historial de IA IXB (parcial)

Seis GET en `project_ai.py` conservan los servicios y errores anteriores:
cliente, análisis guardado, memoria, minutas, carpetas y archivos Drive.
Mantienen alcance total y permisos originales: carpetas exige
`manage_integrations`; las demás lecturas, `view_operations`.
`ixs_ai_sources.js` coordina fuentes, historial y Drive por API, conserva
resultados parciales y reintento, y evita respuestas tardías. Tres CSS externos
conservan IDs y orden del diseño anterior.

Evidencia: 43 pruebas API y 13 e2e aprobadas, incluidas nueve comparaciones
completa/vacía/parcial a 1450/900/390 px. Capturas en
`tmp/migration/project_detail/ixs_ai_sources/`; inspeccionada escritorio.
Regresión dirigida de entrada, Azure, IA y soporte: 91 aprobadas.
Node completo: 176 aprobadas y los tres fallos previos. Ruff/formato, Django
y diff aprobados; mypy conserva seis errores anteriores en otros archivos.
Fuentes simuladas, sin consultas reales a modelos, Drive, Azure o Gmail.

**IA y fase 10 siguen parciales:** contexto/cálculos, presentación y acciones
de generación/preguntas/formularios permanecen anteriores. Continuar por modelo
y vista sin cambiar cálculos; después acciones con permisos y CSRF.

### Fase 10: estructura, tabla y acciones de Azure DevOps IXB

La entrada `ixs_azure_tab.js` monta la pestaña con estructura DOM segura en
`ixs_azure_tab_view.js`, reutilizando carga, resumen y agrupaciones. Tabla
compartida con Planeación en modo Azure; conserva comentarios visibles,
plegable inicial, controles, etiquetas y filtros. Modelo de filtros/opciones/
títulos en `ixs_azure_table_model.js`, probado contra las funciones originales.
Escrituras con las API v1 existentes, CSRF, edición y alcance total del servidor.

Las acciones compartidas mantienen la diferencia original: una fecha guardada
en Azure solo recalcula su fila; en Planeación también actualiza las alertas.
Sesiones y filas protegen contra respuestas tardías; comentarios conservan
validación, errores, borrador y confirmación temporal. Actualizar conserva
filtros y búsqueda, y se puede buscar en el corte previo mientras llega otro.

Pruebas nuevas: dos Node y 35 e2e, con nueve comparaciones de pestaña y quince
de guardado a 1450/900/390 px, filtros/fechas, errores/reintentos, resultados
tardíos, texto seguro y datos previos en carga. Capturas en
`tmp/migration/project_detail/ixs_azure_table/`.
Regresión final: 152 aprobadas (100 e2e, 41 API y 11 soporte frontend),
incluida Planeación y sus casos tardíos de Work Items. Node completo: 170
aprobadas y los tres fallos anteriores (`cost_sprint_details`,
`executive_report`, `financial`). Ruff/formato y diff aprobados; captura
completa de escritorio inspeccionada. Fuentes simuladas, sin publicar nada en
Azure/Gmail; no se presenta como regresión completa del portal.

**Azure DevOps está migrada; fase 10 parcial.** Quedan IA, Cliente/Acciones,
Comunicación, pestañas AER y estructura compartida. La entrada global sigue
cargando el archivo anterior por esos apartados: no retirarlo ni retirar el shim.

### Fase 10: indicadores y resumen de Azure DevOps IXB (parcial)

`sections/ixs_azure_summary{,_model,_view}.js` presenta indicadores, salud/dona,
avisos, atención prioritaria, carga por persona, próximas fechas y estados.
DOM seguro/eventos externos, colores y barras por CSSOM, estilos externos.
Conserva todas las fórmulas, denominadores, clasificaciones, orden y límites
de listas. Ver más/menos y reinicio al actualizar ya son modulares.

Evidencia: cinco Node contra las variables calculadas en la función original;
16 e2e aprobadas, con doce comparaciones de todos los elementos a 1450/900/390 px
(completa, vacía, cerrados y sin detalle), tres pruebas de expandir/contraer/
actualizar y texto seguro. Capturas en
`tmp/migration/project_detail/ixs_azure_summary/`, inspeccionada escritorio.
Regresión dirigida de grupos/cargas/entrada/soporte y guardados visibles:
58 aprobadas adicionales. Node completo: 168 aprobadas y los mismos tres
fallos previos (`cost_sprint_details`, `executive_report`, `financial`).
Ruff/formato y diff aprobados. Fuentes simuladas; no se ejecutó todo el portal.

**Pendiente en Azure:** estructura de la pestaña, selectores, filtros y tabla
editable con sus acciones. No se da por migrada toda la pestaña ni la fase 10.

### Fase 10: agrupaciones y desgloses de Azure DevOps IXB (parcial)

`sections/ixs_azure_groups{,_model,_view}.js` separa personas, iteraciones,
etapas, búsqueda y ventanas de detalle. Conserva clasificación, orden y
conteos con tres pruebas Node contra las funciones originales. DOM seguro,
eventos externos, mismo foco y cierre por botón/fondo/Escape; sin nuevas API.
CSS externo iguala `.top` dentro de las ventanas con la pantalla anterior.

22 pruebas e2e aprobadas: comparaciones de todos los elementos de grupos
(completa/vacía/aviso) y ventanas (persona/iteración/etapa) a 1450/900/390 px,
además de búsqueda, cierre y texto seguro. La prueba espera al final de la
animación de la flecha, sin modificar el producto. Capturas en
`tmp/migration/project_detail/ixs_azure_groups/`.
Regresión dirigida de cargas/entrada/soporte frontend y escrituras visibles:
36 aprobadas adicionales. Node completo: 163 aprobadas y los mismos tres
fallos anteriores (`cost_sprint_details`, `executive_report`, `financial`).
Ruff/formato y diff aprobados; no se ejecutó la suite completa del portal.

**No es la pestaña completa:** faltan indicadores/resumen, atención prioritaria,
carga, próximas fechas, estructura y tabla editable con filtros/acciones.
La fase 10 continúa parcial; la ruta anterior y el shim se conservan.

### Fase 10: transporte y cargas de Azure DevOps IXB (parcial)

`screens/proyectos/<id>/azure/?forzar=1` reutiliza `get_ixs_panel` y su caché,
sin modificar servicios, cálculos o permisos. La lectura diferida de Planeación
permanece separada y no fuerza refresco. Controlador/modelo/mensajes en
`sections/ixs_azure{,_model,_loading}.js`; carga y errores por DOM seguro,
consultas protegidas contra respuestas tardías y recargas de la misma pestaña.
La ruta anterior conserva RPC y su cargador independiente.

**No equivale a pestaña migrada:** resumen, agrupaciones, filtros, tablas,
desgloses y acciones aún se ejecutan en `proyecto_detalle.js`; deben ser el
siguiente bloque. La fase 10 sigue parcial.

Evidencia: 12 pruebas nuevas API, 5 Node del modelo/controlador y una nueva
del cliente; 14 e2e (nueve comparaciones de cajas/estilos contra la anterior a
1450/900/390 px, carga, actualización, filtros/desglose, respuestas tardías,
error seguro y reintento). Específicas junto con Planeación/alta RAID: 48 API y
11 Node aprobadas. Capturas en `tmp/migration/project_detail/ixs_azure_transport/`.
Ruff, formato y comprobación de Django aprobados. Mypy conserva seis errores
anteriores en cuatro archivos, confirmados ejecutándolo también con la versión
de la API en HEAD (`--shadow-file`); detalle en `docs/estado-traspaso.md`.
Regresión del detalle, Planeación, API y soporte frontend: **181 aprobadas**
con Chrome. Node completo: **160 aprobadas y tres fallos anteriores**
(`cost_sprint_details`, `executive_report`, `financial`). No se ejecutó una
nueva regresión completa de todas las pantallas del portal.

### Fase 10: escrituras/comentarios de Work Items (Planeación parcial)

API v1 `screens/work-items/<id>/{avance,comentarios}/`: POST con el mismo
`daily.save_work_item_progress` y `daily.add_comment`, sin modificar servicios,
proyecto activo, validaciones ni fecha local que se añade al comentario.
ID de ruta autoritativo, cuerpo objeto, errores públicos para excepciones y
contrato `{data, meta}`. Exige edición y alcance total igual que el RPC;
CSRF también en comentario por herencia y aun con accesos apagados. Son
servicios globales por Work Item, no se finge validar pertenencia a una cuenta.

`ixs_work_item_actions.js` maneja los cuatro campos y comentarios en Planeación.
La actualización de la barra usa DOM seguro/CSS externo, la misma ecuación y
los valores actuales de los controles. Mantiene las alertas de errores, trim,
validación de comentario vacío, mensajes y sus tres segundos; protege frente
a respuestas de otra sesión/fila desmontada y doble envío de comentario.
Fecha límite conserva la mutación del item y el repintado de alertas existente.
La pestaña Azure anterior también usa estas dos APIs mediante `workItemCall`,
pero mantiene por ahora su controlador y presentación previos. La comparación
anterior conserva RPC: no contar la pestaña Azure como migrada por ese puente.

La columna de comentarios de Planeación está oculta por el CSS original y se
conserva así. Las pruebas del controlador usan eventos DOM sin mostrarla; se
prueba también un envío con controles visibles desde Azure DevOps. No se
publican comentarios reales, las fuentes de prueba están simuladas.

Veintinueve pruebas API nuevas verifican servicio/valores exactos (incluidos
false/0), respuesta, método, cuerpo, edición/alcance antes del servicio,
CSRF y errores. Veinticinco de navegador prueban doce comparaciones visuales
tras guardar a 1450/900/390 px, los cuatro campos y CSRF del cliente, comentarios
vacíos, errores de fuente/transporte/permisos, reintento, doble envío y
respuestas tardías. Dos Node nuevos contrastan el contrato del cliente y la
ecuación contra el recálculo original. Específicas: **80 aprobadas**, incluidas
26 de la presentación de Planeación. Capturas:
`tmp/migration/project_detail/ixs_work_items/<caso>/<ancho>/`.

Regresión de proyecto: **321 aprobadas** en APIs del detalle/Recursos/
Planeación/Work Items, soporte frontend y vistas migradas AER/IXS, con Chrome.
No se presenta como una nueva regresión completa del portal. JavaScript:
**140 aprobadas y tres fallos anteriores** (`cost_sprint_details`,
`executive_report`, `financial`). Ruff, formato, mypy de la API,
comprobación de Django y revisión del diff aprobados.

**Siguiente:** editor de hitos del histórico y extensión con integraciones.
Planeación y la fase 10 continúan parciales; mantener shim/JS anterior.

### Fase 10: presentación y cargas de Planeación IXB/SaaS/RaaS (parcial)

Modelo, vista y controlador en `sections/ixs_planning*.js`: seis indicadores,
alertas de plazos/ausencias, resumen y distribución de Work Items por etapa,
calendario de seis semanas, registros de vacaciones y tabla Azure con filtros
locales. DOM seguro y eventos externos; estáticos en la hoja de Planeación,
barras/colores/coordenadas por CSSOM. Consultas a las APIs existentes, sin
cambiar servicios ni reglas; conserva estados y callbacks para interoperar
con las acciones aún anteriores. Los tokens y la identidad del proyecto
protegen frente a respuestas tardías y recargas de la misma pestaña.

El Gantt reutiliza `timeline()` del Ejecutivo y permite botones de edición
mediante callback opcional. Sin callback el Ejecutivo no cambia. Conserva
índices, categorías, posiciones, eventos simultáneos y editor anterior del
hito histórico. La llegada tardía del histórico actualiza el renderizador
modular, sin insertar HTML de la versión previa. La tabla mantiene sus IDs,
campos y acciones de edición/comentario, delegadas a sus controladores
existentes: sus escrituras y recálculo siguen pendientes de migración.

Las dos pruebas Node nuevas contrastan los modelos contra las funciones
originales para plazos/estados, indicadores, ranking y personas distintas por
semana, sin mutar las fuentes. Treinta pruebas existentes de Planeación y
26 nuevas de navegador aprobaron: dieciocho variantes a 1450/900/390 px (vacía,
errores de fuente, alertas, eventos simultáneos y textos ausentes), dos comparaciones de carga,
respuestas tardías entre pestañas/proyectos, acciones/navegación, edición del
marcador, histórico diferido y texto seguro. Capturas:
`tmp/migration/project_detail/ixs_planning_view/<caso>/<ancho>/`.

Regresión de proyecto: **264 aprobadas** (APIs, soporte frontend y vistas
migradas AER/IXS). Después se ajustaron ID/título ausentes de Azure para
conservar el texto vacío del original y se añadieron tres comparaciones;
las **36 finales** de vista/transporte aprobaron. No se presenta como una
nueva regresión completa del portal. JavaScript: **138 aprobadas y tres
fallos anteriores** (`cost_sprint_details`, `executive_report`, `financial`).
Ruff, formato, comprobación de Django y revisión del diff aprobados.

**Siguiente:** escrituras/comentarios y actualización visual de Work Items;
después editor de hitos del histórico y extensión con sus integraciones.
Esas acciones todavía usan RPC y controladores previos; no contar Planeación
ni la fase 10 como terminadas, ni retirar aún el shim y el JS anterior.

### Fase 10: editores de Planeación IXB/SaaS/RaaS (parcial)

`sections/ixs_planning_editor_model.js`, `_view.js` y `.js` separan campos,
DOM y controlador de los formularios. La ruta activa abre el módulo desde
el puente anterior; la comparación mantiene sus formularios independientes.
CSS externo en `project_detail_ixs_planning.css`. No se cambian cálculos,
fuentes, permisos, campos requeridos ni opciones. Save/delete usan las APIs
del bloque anterior, manteniendo el ID y UID exactos y confirmación de borrado.

El controlador bloquea doble envío, conserva datos ante errores y permite
reintentar. Cada apertura identifica su propia sesión, para descartar respuestas
de formularios cerrados o de otro proyecto sin cerrar un editor recién abierto.
La selección inicial de Hito no modifica los registros recibidos.

Veinte pruebas nuevas de navegador y diez de transporte aprobadas: doce
comparaciones con la anterior a 1450/900/390 px, incluidos campos, valores,
opciones y required; edición y borrado de ambos tipos con UID especial,
confirmación, errores de fuente/transporte/permisos y reintento; doble envío,
respuestas tardías de éxito/error, texto seguro y cancelación. Capturas:
`tmp/migration/project_detail/ixs_planning_editor/<tipo>/<modo>/<ancho>/`.
La comprobación inicial contó `style=""` que agrega el normalizador compartido;
se exige cero declaraciones CSS y cero eventos inline sin cambiar ese código.

Regresión del bloque: **241 aprobadas** en APIs del detalle/Recursos/Planeación,
soporte frontend y todas las vistas de proyecto ya migradas (entrada, ambos
Ejecutivos, Esfuerzo, Recursos, transporte y editores de Planeación), con Chrome.
No se presenta como una nueva regresión completa del portal. JavaScript:
**136 aprobadas y tres fallos anteriores** (`cost_sprint_details`,
`executive_report`, `financial`). Ruff, formato, comprobación de Django y
revisión del diff aprobados. Sin cambios de Python de aplicación ni de servicios.

**Siguiente:** extraer la presentación general de Planeación y sus cargas,
incluidos calendario y Gantt editable. Sus acciones de Azure y la extensión
con integraciones aún dependen de componentes anteriores. Esta pestaña y la
fase 10 siguen parciales.

### Fase 10: transporte de Planeación IXB/SaaS/RaaS (parcial)

La ruta activa consulta `.../<id>/planeacion/` y `.../planeacion/azure/`.
Usan exactamente `read_plan` con el store anterior y `get_ixs_panel(id, False)`;
se conservan caché, filtros y errores del panel. El alta/edición y borrado usan
POST a `.../planeacion/<tipo>/{guardar,eliminar}/`, con `save_plan` y
`delete_plan` sin alterar sus reglas. El ID de la ruta prevalece sobre el del
cuerpo; el UID se conserva exactamente, sin incluirlo en la URL.

Las lecturas exigen `view_operations` y alcance total; las escrituras,
`edit_operations`, alcance total y CSRF aun con accesos apagados. El servicio
existente sigue validando tipos, fechas y pertenencia del UID al proyecto.
El cliente compartido conserva los 90 segundos y el manejo de CSRF.
Un puente temporal de cuatro operaciones mantiene los callbacks, estados,
errores y protección ante respuestas tardías del controlador anterior.
La ruta de comparación conserva su transporte RPC independiente.

Las pruebas de servidor cubren contratos de lectura, fuentes, ID exacto,
permisos antes del servicio, métodos, tipos de cuerpo, CSRF heredado también
en borrado y errores públicos. Las de navegador comparan página/editor con
la anterior a 1450/900/390 px y ejercitan altas, edición, borrado,
errores/reintento, resúmenes y filtros locales de Azure. Capturas:
`tmp/migration/project_detail/ixs_planning_transport/<ancho>/`.

Validación final: **1427 aprobadas, una omitida** en portal/core/access/e2e
con Chrome, excluyendo los cuatro temporales ajenos. Incluye 94 pruebas API
del detalle/planeación y diez de navegador de este bloque. JavaScript:
**136 aprobadas y tres fallos anteriores** (`cost_sprint_details`,
`executive_report`, `financial`). Ruff, formato, mypy de la API y revisión de
Django aprobados. Los primeros intentos restringidos no iniciaban Chrome;
la corrida específica (103, antes de añadir el filtro Azure) y la regresión
final aprobaron ejecutándolo fuera de ese entorno.

**Pendiente de esta pestaña:** separar modelo, vista y controlador (incluidos
Gantt editable, calendario y editores); migrar las ediciones/comentarios de
Work Items y la extensión con sus integraciones. Su presentación todavía
usa `proyecto_detalle.js`: no marcar Planeación ni la fase 10 como terminadas.

### Fase 10: primer bloque, entrada y lecturas iniciales

`pages.project_detail` usa `_modern` y la vista original conserva su contexto
mediante `render_page`. `main.js` instala la conexión de datos antes de cargar
el componente anterior; `data.js` usa el cliente compartido con timeout de
90 segundos. Solo filtros, carga inicial y Actualizar dejan de usar RPC.
Los endpoints invocan los mismos servicios Python; no cambian cálculos,
redondeos, cachés ni fuentes. Las respuestas originales quedan en `{data, meta}`.
Se conserva la denegación de alcance limitado de esas lecturas RPC: los
servicios todavía contienen datos del portafolio que no están recortados.

El cuerpo inicial de la plantilla no tiene estilos o eventos en línea,
pero los componentes anteriores todavía los generan. El JS de un megabyte,
su CSS y el shim se mantienen como dependencia transitoria, sin copiarlos
a `frontend/`. **No dar por terminada la pantalla ni la fase 10.**
La comparación con `?vista=anterior` conserva el transporte RPC anterior.
Pruebas en `test_project_detail_api.py` y `test_project_detail_entry.py`:
contratos, IDs con CR, acceso antes de fuentes, errores y reintentos,
selección de pestaña y capturas AER/IXB a 1450 y 390 px. Dos pruebas Node
verifican rutas exactas, timeout y propagación de errores. Los recorridos
Node anteriores siguen ejercitando RPC con los helpers reales.

Validación del bloque: **21 pruebas de API, diez de navegador y dos anteriores
del contenedor** aprobadas (33 juntas). Regresión general: **1248 aprobadas,
una omitida**. JS completo: **124 aprobadas y los tres fallos anteriores**
(`cost_sprint_details`, `executive_report`, `financial`). Ruff, formato, mypy y
`manage.py check` aprobados. Los cambios pendientes ajenos siguen fuera.

### Fase 10: Ejecutivo AER/T&M

`sections/aer_executive.js` construye el contenido con nodos DOM seguros y
eventos externos. `aer_executive_model.js` conserva las reglas originales de
presentación, orden, prioridades, salud, dependencias, fechas y redondeos.
El controlador anterior delega solo esa pestaña en el módulo nuevo; los enlaces
a Acciones, Planeación y Riesgos siguen llamando al controlador existente.
No hay servicios, cálculos de backend ni permisos modificados.

Los estilos AER compartidos se extrajeron a `project_detail_aer.css`, sin
cambiar sus reglas. El enlace con ID `aer-dashboard-styles` evita inyectarlos
desde el JS anterior en la ruta nueva; la anterior conserva su propia fuente
CSS en línea. Las declaraciones estáticas del HTML ejecutivo están en
`project_detail_aer_executive.css`; los valores de las barras usan CSSOM.
Las demás pestañas aún conservan sus componentes, eventos HTML y RPC.

Trece pruebas de navegador nuevas comparan cada elemento, cifras, fuentes,
estilos y cajas contra el anterior en 1450, 900 y 390 px (completo, vacío y
atención); verifican enlaces por teclado, regreso y texto sin interpretar HTML.
Capturas: `tmp/migration/project_detail/aer_executive/<caso>/<ancho>/`.
Dos pruebas Node contrastan el modelo en 27 escenarios con el renderer original,
incluidos sus umbrales y fallbacks; también formatos y dimensiones sin fuente.
El diseño anterior permanece independiente para mantener esa comparación.

Regresión general: **1261 aprobadas, una omitida**; incluye las trece nuevas
pruebas de Ejecutivo y las diez existentes de su entrada. JS completo:
**126 aprobadas y los tres fallos anteriores** (`cost_sprint_details`,
`executive_report`, `financial`). Ruff, formato y comprobación de Django
aprobados. Los servicios y los pendientes ajenos se conservaron sin cambios.

El Ejecutivo IXB/SaaS/RaaS se completó en el bloque siguiente, descrito abajo.
El detalle completo y la fase 10 continúan parciales.

### Fase 10: Ejecutivo IXB/SaaS/RaaS

Modelo, vista y controlador separados en `sections/ixs_executive_model.js`,
`ixs_executive_view.js` e `ixs_executive.js`. El contenido usa nodos seguros,
sin `innerHTML` con datos ni eventos HTML. Los iconos originales se conservan
en `ixs_icons.js`. Las reglas IXS compartidas se extrajeron íntegramente a
`project_detail_ixs.css`; el enlace `ixs-v74-styles` evita su inyección en la
ruta nueva. Los estilos estáticos del ejecutivo tienen su propia hoja;
los valores dinámicos de barras y gráfica usan CSSOM.

RAID, tasks, etapas históricas y estados de recursos tienen cuatro lecturas
API v1 con los mismos servicios, ID exacto, manejo de errores y alcance total
del RPC. No se cambian cálculos ni permisos. Se mantienen las actualizaciones
parciales originales: el histórico completa el Gantt, los estados marcan
recursos inactivos y cada fuente conserva su error independiente. Las
respuestas de un ejecutivo desmontado no sustituyen uno recién abierto.
Planeación sigue usando su Gantt editable anterior.

Catorce pruebas nuevas de navegador: nueve comparaciones de cada elemento
(completo, vacío y alertas a 1450, 900 y 390 px), consultas diferidas, expansión
por teclado, errores de fuente/transporte, recuperación al regresar, texto
seguro y respuestas tardías. Capturas y diferencias en
`tmp/migration/project_detail/ixs_executive/<caso>/<ancho>/`.
Dos pruebas Node contrastan 32 escenarios ejecutivos y diez de línea de
tiempo con las funciones originales; también se amplió el contrato de rutas,
ID con CR y timeout de 90 segundos. La API tiene pruebas de payloads,
permisos antes de las fuentes y reutilización de repositorios/servicios.

Validación: **48 pruebas API y catorce de navegador aprobadas** para este
bloque; las diez de la entrada también pasan. Regresión general: **1302
aprobadas, una omitida**. JavaScript: **128 aprobadas, tres fallos anteriores**
(`cost_sprint_details`, `executive_report`, `financial`). Ruff, formato,
mypy de la API y comprobación de Django aprobados. Sin cambios en servicios,
permisos, Horas por mes ni pendientes ajenos.

Esfuerzo IXB/SaaS/RaaS se completó en el bloque siguiente, descrito abajo.
El detalle completo sigue parcial.

### Fase 10: Esfuerzo IXB/SaaS/RaaS

Modelo, vista, controles y ventanas en `sections/ixs_effort*.js`:
indicadores y tabla por recurso; mix, actividades y tendencia; registros con
semana local por defecto y filtro de fechas; detalle por actividad/recurso;
lista completa de registros y excedidas por persona. Esta última conserva
las fechas, desplegables, orden por columna, ocho filas por página y CSV.
El contenido se construye con nodos seguros y eventos externos; las tres
declaraciones estáticas adicionales viven en `project_detail_ixs_effort.css`.
Se reutilizan iconos, barras, formatos y expansión de horas del Ejecutivo.

`screens/proyectos/<id>/registros/` invoca `project_entries` con el mismo
repositorio, ID, manejo de errores y alcance total del RPC. Tasks y estados
de recursos reutilizan las lecturas anteriores. La caché conserva los
registros y las fechas al volver a la pestaña, y se reinicia al cambiar de
proyecto aunque no se visite Esfuerzo en el intermedio. Las cargas tardías
no sustituyen otra pestaña ni otro proyecto. Se conserva también la caché
del error de registros del comportamiento anterior.

Sin cambios en los cálculos: se conservaron los totales y sus fallbacks,
la agrupación por actividad/persona y últimos cinco meses; las excedidas
siguen calculándose cronológicamente sobre todo el historial facturable,
con deduplicación por ID y solo la fracción que cruza el presupuesto. El
filtro de fechas se aplica después de ese cálculo. El CSV conserva BOM,
columnas, fechas, cuatro decimales para excedidas, nombre y protección de
fórmulas. El CSV original y nuevo se comparan byte por byte en navegador.

Veinticinco pruebas nuevas de navegador: nueve comparaciones del contenido
(completo, vacío y alertas) y nueve de las tres ventanas a 1450/900/390 px;
fechas, caché, navegación, orden, paginación, CSV, errores de fuente/transporte,
texto seguro, Escape y respuestas tardías. Capturas y diferencias en
`tmp/migration/project_detail/ixs_effort/<caso>/<ancho>/`. Cuatro pruebas Node
contrastan doce escenarios de totales, agrupaciones/excedidas con el código
original, semanas locales y caché entre proyectos. Contratos y permisos de
API ampliados para la nueva lectura.

Validación específica: **55 pruebas API y 25 nuevas de navegador**; junto
con las catorce del Ejecutivo IXB aprobaron **94**. JavaScript completo:
**132 aprobadas y tres fallos anteriores** (`cost_sprint_details`,
`executive_report`, `financial`). Ruff, formato, mypy de la API y comprobación
de Django aprobados.

Regresión final: **1334 aprobadas, una omitida**. En la primera corrida
aprobaron 1333 y falló la prueba de respuestas tardías del Ejecutivo: su
interceptor retenía además la nueva consulta de tasks de Esfuerzo. Se ajustó
para retener solo las lecturas del primer Ejecutivo y se repitieron las 94
pruebas del bloque y la regresión completa, ambas aprobadas. No se cambió
la comprobación de que una respuesta obsoleta no sustituya el contenido.

Recursos IXB/SaaS/RaaS se completó en el bloque siguiente, descrito abajo.
La pantalla completa y la fase 10 siguen parciales.

### Fase 10: Recursos IXB/SaaS/RaaS

`sections/ixs_resources_model.js`, `ixs_resources_view.js` e
`ixs_resources.js` separan la mezcla de asignaciones, presentación y controles.
Conservan la normalización por nombre, prioridad de las asignaciones sobre
la base ejecutiva, sumas de todos los registros del ID, orden alfabético,
saldos y alertas de recursos sin asignación o inactivos con horas. El editor
permite agregar, editar rol/estimación/estado y asignar a quien tiene horas;
conserva el nombre de solo lectura al editar. No cambian cálculos ni servicios.
DOM seguro, eventos externos y cinco reglas estáticas de CSS en
`project_detail_ixs_resources.css` sustituyen el HTML y estilos en línea.

Las lecturas reutilizan `recursos/` y `registros/`, en el mismo orden y
con cargas/errores parciales iguales. Cada apertura vuelve a consultar.
`POST .../recursos/guardar/` llama al mismo `save_resource` sobre el mismo
store, con las validaciones originales. El ID de la ruta prevalece sobre
el cuerpo; no permite dirigir el guardado a otro ID mediante el JSON.
Exige `edit_operations` y alcance total, como RPC, y CSRF también con los
accesos apagados. El cliente usa `apiSend` y el timeout anterior de 90 segundos.

Guardar bloquea envíos duplicados, conserva el formulario ante error y permite
reintentar. El éxito actualiza la tabla e invalida los estados de recursos que
releen Ejecutivo/Esfuerzo. Las respuestas tardías no sustituyen otra lectura,
proyecto o pestaña. Los controles conservan su visibilidad anterior;
el permiso de escritura se valida en el servidor.

Treinta y una pruebas nuevas de navegador: doce comparaciones del contenido
(completo, vacío y errores de asignaciones/Clockify), nueve del editor
(agregar, editar, asignar) a 1450/900/390 px y dos de carga a 1450/390 px.
También prueban altas, cambios, asignación, CSRF del cliente, reintentos por
errores de fuente/transporte/permisos, bloqueo de doble envío, invalidación
de estados, cancelación, texto seguro y respuestas tardías. Capturas en
`tmp/migration/project_detail/ixs_resources/<caso>/<ancho>/`.
Trece pruebas nuevas de API verifican payload/ID, permisos antes del servicio,
CSRF, validación de cuerpo y la llamada al servicio anterior. Dos pruebas Node
contrastan mezcla/horas/alertas y fuente del editor con las funciones originales;
otra prueba del cliente valida POST, ID con CR, payload y timeout.

Validación específica: **44 aprobadas** (31 de navegador, trece de API).
JavaScript: **135 aprobadas y tres fallos anteriores** (`cost_sprint_details`,
`executive_report`, `financial`). Ruff, formato, mypy de la API y comprobación
de Django aprobados. Los servicios y los cambios pendientes ajenos se conservaron.

Regresión final: **1378 aprobadas, una omitida**. La primera corrida se detuvo
con 700 aprobadas y dos fallos de la prueba de carga: Playwright pasaba
`request` al segundo argumento del interceptor, usado por error para enlazar
una lista. Se corrigió con un cierre de fábrica, conservando la comparación
estricta; las 44 pruebas específicas y la regresión completa aprobaron después.

**Siguiente bloque: Planeación IXB/SaaS/RaaS**. Después las demás pestañas.
El detalle grande y la fase 10 siguen parciales; el shim y el JS anterior
siguen siendo necesarios.

Proyecto simple (`proyecto/<id>/`) usa `pages.project` y `render_page`,
con las mismas funciones de portafolio y detalle, permisos por proyecto y
cuenta, fechas, redondeos y estados de fuente. CSS y presentación de barras
están separados en `project.css` y `project/main.js`; los valores siguen
calculándose en Python. No requiere otro endpoint ni modifica el detalle
grande (`proyectos/<id>/`). Siete pruebas de servidor verifican ruta activa,
alternativa temporal, expiración, solo lectura y acceso; seis de navegador
validan datos, regreso, carga parcial y paridad visual. Capturas reproducibles
en `tmp/migration/project/<ancho>/<full|empty>/`. Se comparan también los
estados vacíos y el error parcial conservando cifras conocidas. Regresión
general: **1215 aprobadas, una omitida**; tras ampliar esos estados visuales,
el cierre dirigido de Proyecto simple aprobó **19 pruebas**, incluidas sus
seis pruebas de cálculo anteriores, sin modificarlas. Ruff, formato, mypy y
`manage.py check` aprobados. JS completo: **122 aprobadas y los tres fallos
anteriores** documentados. El desbordamiento de las cuadrículas en
móvil ya existe en la pantalla anterior y se conserva en esta migración.

### Pendientes que no se dan por hechos

Actualización al retomar el traspaso: Inversión completada sobre los cambios
pendientes de Claude. No se modificó `inversion_data` ni el cálculo de GSE.
Se corrigió la prioridad CSS del margen del segundo encabezado. Cinco pruebas
e2e verifican totales, anchos de barras, cambio de mes, regreso, error de fuente
y paridad visual en escritorio, tableta y móvil. Las capturas reproducibles
se guardan en `tmp/migration/investment/` al ejecutar las pruebas con Chrome.
Inversión registrada en `0028959`. También se completaron las asignaciones
mensuales de Capacidad: formulario GET, permisos, cálculos y CSV originales;
CSS separado y eventos sin atributos en línea. Se mantuvo su modelo de caja
con una clase explícita, sin alterar el resto de las pantallas. Tres pruebas
e2e aprobadas con capturas reproducibles en `tmp/migration/capacity/`.
También se completó el detalle diario de Capacidad (`/capacidad-instalada/`).
La ruta activa usa plantilla y CSS de `frontend/`; el JS se separa en
`capacity_daily/model.js`, `view.js` y `main.js`. No genera HTML con datos ni
usa el adaptador RPC. Las dos lecturas API invocan las mismas funciones Python
de Capacidad; no se modificaron sus reglas, fuentes o cálculos. El modelo puro
se contrasta en Node con la implementación anterior para datos conocidos,
pendientes, proyectos fuera del mes y personas compartidas. La actualización
conserva como máximo dos consultas de proyectos simultáneas y descarta
respuestas de una selección anterior. Las pruebas verifican también que la
API rechace alcance limitado antes de leer fuentes. Capturas reproducibles:
`tmp/migration/capacity_daily/<ancho>/<matrix|people>/`.
Facturabilidad general, especialidad y recurso también usan sus plantillas
modulares, CSS y controladores separados. Los datos continúan saliendo de
las mismas funciones Python; no se cambiaron fórmulas, unidades ni alcance.
El selector de periodo se comparte con el existente, mediante un enlace de
eventos reutilizable para la plantilla del servidor. Las alturas de barras
usan los valores del servidor mediante CSSOM, sin estilos en la plantilla.
Doce pruebas de navegador comparan celdas, cajas y estilos contra las
pantallas anteriores a 1450 y 390 px, incluyendo selectores abiertos.
Doce pruebas de servidor verifican plantillas activas y rechazo antes de
leer fuentes para usuarios anónimos, sin permiso o con alcance limitado.
Capturas: `tmp/migration/billability/<general|especialidad|recurso>/<ancho>/`.
Comportamiento anterior conservado: las pestañas trasladan el periodo, pero
no el filtro de roles. Los cambios de periodo sí conservan ese filtro.
Facturabilidad por área también está migrada: los cinco apartados conservan
su presentación y utilizan DOM seguro, con módulos de modelo, controlador,
vista, recursos, horas, KPIs y área seleccionada. Las APIs llaman a los mismos
servicios de `apps/gse/rpc.py` directamente; no modifican esos servicios ni
la base. Se conservan lotes, deduplicación por ID, caché anual, errores por
mes, estados parciales, bandas, bajas, festivos, jornadas, búsqueda, servicios
desplegables, paginación y CSV. Cache e IDs mantienen el alcance total y
exigen CSRF también en modo local sin permisos activados. La lectura fallida
de áreas se puede reintentar con el botón de consulta existente.
Las dos pruebas de modelo Node contrastan agregados, capacidad laboral,
bandas, clasificación, pesos de KPIs y resultados parciales con el JS anterior.
La comparación visual de los cinco apartados y el área seleccionada verifica
también el texto de las tablas. Capturas:
`tmp/migration/billability_area/<ancho>/<apartado>/`.
Limitación anterior conservada: el CSS oculta la navegación de apartados en
pantallas pequeñas. La comparación móvil selecciona antes el apartado en
escritorio y luego cambia el ancho; no acredita navegación móvil entre ellos.
No se alteró ese diseño dentro de la migración.
EVA 1–3 completadas con el contexto Python original y módulos separados.
Los históricos activos se leen como JSON y se construyen con nodos DOM;
no se inserta HTML con datos. El formato de las cifras del histórico sigue
usando los mismos filtros de Django, incluidos agrupación y decimales.
EVA 1 conserva filtros de fechas, servicio y DM, conteo y CSV. EVA 2 conserva
su presentación distinta y no recibe funciones nuevas. EVA 3 conserva la
consulta diferida, lotes de dos IDs, promedio de los proyectos con consumo
conocido, lectura del histórico de MPB en 2026, guardado de Burn pendiente
en MPB y hasta dos consultas de cerrados simultáneas. No se cambiaron sus
umbrales ni redondeos. Las APIs validan alcance total antes de leer fuentes;
los POST exigen CSRF y delegan en los servicios originales.
Los fragmentos HTML anteriores se conservan para comparación, con la ruta
activa sirviendo su equivalente de `frontend/`. Las pruebas de comparación
solicitan explícitamente el fragmento original con `?vista=anterior`.
Quince pruebas e2e y 29 de API cubren las tres pantallas; dos pruebas Node
contrastan filtros/CSV y promedio contra los scripts anteriores.
Ruff, formato, mypy y comprobación de Django aprobados. JS completo:
122 aprobadas y tres fallos anteriores. La regresión completa no quedó
totalmente limpia: dos corridas dieron 1203 aprobadas, una omitida y una
fallida cada una, en recorridos de sesión de Acuerdos (primero el cambio de
estado con 403 ya documentado; después la recarga con sesión requerida).
Los dos recorridos y las quince pruebas EVA pasaron juntos después:
19 aprobadas, sin cambiar permisos ni pruebas de Acuerdos. Se conserva
esta limitación de validación para investigarla por separado.
Capturas: `tmp/migration/eva{1,2,3}/<ancho>/`, con histórico abierto y cerrado.
Proyecto simple se completó después; el siguiente bloque es el detalle grande
del proyecto (`proyectos/<id>/`), por pestañas.
Regresión tras completar Facturabilidad por área: **1160 aprobadas y una
omitida**; veinte pruebas e2e de esta pantalla y 41 de API. Ruff, formato,
mypy y `manage.py check` aprobados. JavaScript: 120 aprobadas y los mismos
tres fallos anteriores, cuyos archivos y reglas no cambiaron.
La regresión posterior a estas tres vistas aprobó **1098 pruebas, con una
omitida**. JavaScript conserva 118 aprobadas y los mismos tres fallos del
código anterior. No se activaron permisos ni se modificaron las fuentes.
La regresión tras Capacidad diaria aprobó 1074 pruebas (una omitida), más las
tres pruebas nuevas del modelo JS. Siguen tres fallos documentados del JS
anterior; no pertenecen al nuevo detalle diario.

1. Mantener las pantallas de las fases 7–9 ya migradas según la tabla;
   no rehacer sus migraciones ni modificar sus cálculos.
2. Mantener las comparaciones visuales y los recorridos de las pantallas ya
   migradas, y añadirlos para cada bloque restante.
3. `proyecto_detalle` por pestañas y retirar `/api/rpc/` y `gas_shim.js`.
4. Mover a servicios compartidos la preparación de datos que hoy viven en
   `views.py` y que usan las APIs: `operativa_context`,
   `operativa_block_context`, `operations_summary_data`, `kpi_context`,
   `dm_state`/`dm_rows`, `eva2_data`, `eva3_data`, `inversion_data`,
   `capacidad_data`, `facturabilidad_data`, `especialidad_data`, `recurso_data`
   (y `costos_revenue`). Sin duplicar ni cambiar cálculos.
5. Genesis: `ACCESS_ENFORCED` está apagado y el proveedor es
   `DjangoAccessProvider` (alcance completo a toda persona con sesión). Falta
   identidad, capacidades y alcance reales por cuenta y proyecto, y que el
   frontend adapte menús y acciones a `me/` (hoy el menú no se oculta).
6. CSP: por defecto **no hay política** (`CSP_REPORT_ONLY` solo se enciende con
   `1` y solo reporta). No hay bloqueo obligatorio y no puede haberlo mientras
   haya scripts y estilos en línea (23 plantillas anteriores).
7. Limpieza final de plantillas, estilos y scripts anteriores, una vez
   migrados y validados todos sus consumidores.

> **Regla de diseño (22/10/2026).** Una pantalla migrada se ve idéntica a la
> anterior; solo cambian los datos, el alcance y los permisos. Se comprueba con
> capturas lado a lado (anterior contra nueva) antes de retirar la anterior. Las
> pantallas ya migradas conservan el diseño anterior en `frontend/`. Las
> plantillas anteriores solo sirven de referencia temporal. Igualar primero
> iconos, degradados, tarjetas y comportamiento antes de retirar esa referencia.

Son **12 fases (0 a 11)**: los cambios del 22/10 agregan la 6 y reubican el
resto. Cada fase es un conjunto de commits en `main`, con la suite en verde.

## Reglas que se mantienen

Actualización para la fase 7: incorporar los nombres y campos solicitados por
Florencia en [cambios-florencia-2026-10-22.md](cambios-florencia-2026-10-22.md).
Bookings, revenue operado y cobrado quedan separados. La fecha de servicio G
es una suposición pendiente de validar con Finanzas (la decisión es suya, no
de la migración); el margen conserva su base.

- Django es el dueño de los datos, los cálculos y la autorización. El frontend
  solo muestra; ocultar un botón nunca sustituye la validación del servidor.
- Una sola fuente de HTML (`frontend/templates`), sin CSS ni JS en línea,
  colores solo en `tokens.css`, nada de `innerHTML` con datos.
- Cada pantalla: un resumen por pantalla en `/api/v1/screens/…`, endpoints
  aparte para desgloses y acciones, errores `{error: {code, message, fields}}`.
- Las cifras del equipo completo no se recortan por cuenta: con alcance
  limitado se ocultan (ver `docs/permisos.md`).
- Antes de migrar una pantalla se fija su comportamiento actual con un
  recorrido en navegador y, si aplica, un snapshot.

## Cambios del 22/10 (reunión del 21/10 y conciliación de KPIs)

Son cuatro piezas, hoy sin confirmar en `main`. Todas pasan la suite actual.

### A. Glosario y diccionario de datos

Qué es: `_executive_glossary.html` (guía desplegable en Business Overview),
textos nuevos en `data_dictionary.CONCEPTS` (comparación de cuentas, tarifa de
costo vendida, tarifa interna de banda, trabajo por entregar, previas al cierre)
y el enlace «Glosario de indicadores».

Riesgo: la misma definición vive en **tres sitios** (el glosario escrito a mano,
`CONCEPTS` y el cajón «Fuentes y cálculo» de `ejecutiva.html`). Se desalinean
con el primer cambio de regla.

Decisión: `CONCEPTS` es la única fuente. Un servicio entrega los conceptos
agrupados (Financiera, Operaciones, Comercial) en `GET /api/v1/reference/glossary/`;
el glosario de Business Overview y la página del diccionario lo dibujan con el
mismo componente `ui/glossary`. Una prueba verifica que cada concepto mostrado
exista en `CONCEPTS`. Contenido y estilo no dependen de Genesis.

### B. Comparación de cuentas en Business Overview

Qué es: `executive_rankings.js` + `_executive_ranking_card.html`. Busca por
cuenta, elige facturación, utilidad bruta o margen, parte las cuentas con dato
en mitad superior e inferior (hasta cinco por grupo, orden invertible), informa
cuántas no aplican y guarda búsqueda y orden en la URL.

Hallazgos:

1. **Alcance.** La página incrusta `financial_snapshot` completo
   (`json_script "financial-cache"`): cualquier persona con sesión recibe la
   facturación y el margen de **todas** las cuentas en el HTML. Con alcance
   limitado esto es una fuga. En la migración el listado sale de una API que lo
   filtra por alcance, y el snapshot deja de incrustarse.
2. **Cifras de empresa.** Los totales de Financiera, cobranza y comercial son
   del portafolio completo: con alcance limitado se ocultan (misma regla que
   Operativa); el listado de cuentas sí se entrega recortado.
3. **Dónde vive la regla.** La partición en mitades y el orden están en JS
   (`rankAccounts`, función pura con pruebas). Se conserva como `lib/ranking.js`
   con las mismas pruebas; si aparece otro consumidor (exportar, reporte) pasa
   a un selector de Python.
4. **Nombres.** El contrato usa `top_half` / `bottom_half`; «Cuentas sanas» y
   «no sanas» quedan como etiquetas de la interfaz. La nota de la pantalla ya
   aclara que son posiciones relativas, no una clasificación validada por
   Finanzas: conviene que las etiquetas no la contradigan.
5. **Dependencias.** Usa `executiveMoney` global (K/M/B) y `innerHTML` escapado
   a mano: pasan a `lib/format.js` (`formatMoney`, con las pruebas de
   `executive_numbers`) y a constructores de `lib/dom.js`.
6. **Navegación.** `ranking_buscar`, `ranking_criterio` y el orden de cada
   grupo se conservan al entrar a una cuenta y regresar: `data/navigation.js`
   (fase 7) debe preservarlos junto con el periodo y `volver`.

### C. Tarifa de costo vendida: pendiente

Qué es: columna «Tarifa de costo vendida» en la comparativa de márgenes
(ya confirmada, `5e7b167`). No se calcula, no se sustituye por la tarifa de
banda y no altera márgenes.

Decisión: el contrato la entrega como
`sold_cost_rate: {value: null, status: "pending_validation"}`. Una prueba
asegura que nunca se deduce de revenue ÷ horas ni de la tarifa de banda. Se
completa cuando Florencia confirme fuente, unidad y asignación.

### D. KPIs de Delivery Managers y conciliación

Qué es: `kpi_quarterly.py` (promedio trimestral de cortes mensuales, puro y con
pruebas), periodo anual por defecto, subcolumnas TP/T/C y notas de unidades
(T = días; C = consumo de horas sobre presupuesto).

Hallazgos:

- **No es un defecto de código.** El documento de conciliación muestra que el
  Excel y la aplicación miden otra cosa: septiembre da TP 9 contra 30, y T y C
  son ratios en el Excel y promedios en la aplicación. Faltan datos de
  negocio (lista de IDs, regla de T y C, si entra Miguel A. y los alias de
  nombres).
- **No se bloquea la migración.** Se migra el cálculo tal como está, con un
  snapshot previo (fase 6), sin tocar umbrales ni importar valores del Excel.
- El contrato manda números sin redondear (los trimestres conservan precisión)
  y las definiciones de TP, T y C como datos, para que no se repitan en HTML.
- Con alcance limitado, las filas se recortan por los proyectos de la persona.

El documento `conciliacion-kpis-dms-2026-10-22.md` queda como registro de lo
pendiente de negocio; no es parte del código.

## Fase 6: línea base de lo nuevo (hecha)

Los cambios del 22/10 quedaron confirmados en cuatro commits (glosario,
comparación de cuentas, documento de interfaz y KPIs de Delivery Managers) y
la línea base quedó fijada:

- `tests/e2e/test_ejecutiva_kpis.py`: glosario, comparación de cuentas
  (criterios, búsqueda sin acentos, orden, valores sin dato, estado en la URL,
  entrar a una cuenta y regresar) y KPIs de Delivery Managers (periodo anual,
  TP/T/C, trimestre como promedio de meses, notas de unidades).
- Snapshots: `ejecutiva_glosario`, `ejecutiva_comparacion` y `kpis_dm_historico`.
- `test_glossary_sources.py`: cada término del glosario declara el concepto del
  diccionario del que sale (se elimina cuando el glosario se genere de
  `CONCEPTS`, fase 8).

Hallazgo para la fase 8: `executive_report.js` todavía dibuja el ranking
anterior (grupos `healthy/unhealthy` y la nota de «indicadores monetarios
normalizados») y `executive_rankings.js` lo vuelve a dibujar encima. Hoy gana el
segundo por el orden de carga; el código viejo debe retirarse al migrar.

Lo que se planeaba para esta fase:

1. Confirmar los cambios del 22/10 en commits separados: glosario y
   diccionario; comparación de cuentas; KPIs DMs. (Hoy comparten `views.py` y
   `ejecutiva.html` con el resto.)
2. Recorridos en navegador sobre las pantallas actuales, antes de migrarlas:
   - Business Overview: abrir el glosario; buscar una cuenta, cambiar el
     criterio, invertir un grupo; entrar a una cuenta y regresar conservando
     búsqueda y orden.
   - KPIs DMs: periodo anual por defecto, histórico mensual y trimestral con
     TP/T/C, trimestre = promedio de meses.
3. Snapshot del texto visible de ambos recorridos.
4. Prueba que fija que el glosario sale de `CONCEPTS`.
5. Corregir la frase «La migración … sigue en pausa» del documento de interfaz.

## Fase 7a: comparativa de márgenes (API hecha; frontend no migrado)

> **Estado real:** los módulos de `frontend/` que esta sección menciona
> (páginas `pages/…`, `ui/detail-dialog`, `ui/agreements`, `data/navigation.js`,
> `lib/account-metrics`…) se retiraron el 22/10/2026 al volver al diseño
> anterior; sobreviven el servicio, la API y las pruebas de la API.

> Nota: la página usa la plantilla anterior; el contrato y el alcance de abajo
> siguen vigentes en la API.


- `GET /api/v1/screens/margenes/` (capacidad `view_costs`): oportunidades con
  `bookings`, `period_revenue`, `operated_revenue` + `operated_revenue_status`,
  `invoiced`, `collected`, `cost`, `sold_cost_rate` (siempre
  `{value: null, status: "pending_validation"}`), márgenes y desviación. Solo
  entrega las cuentas del alcance; una cuenta ajena es 404.
- `POST/GET .../margenes/actualizar/` prepara los costos; `GET /api/v1/costs/project/`
  entrega personas y tarifas de un Project ID (misma capacidad y alcance). El
  desglose anterior (`ejecutiva/costos/`) también valida capacidad y alcance.
- Página `frontend/templates/pages/margenes.html` + `pages/margenes/`; se
  retiraron la plantilla, el CSS y el JS anteriores. `lib/format.js` suma
  `formatMoney` y `formatPercent` (con pruebas).
- El destino de regreso lo sigue validando el servidor (`return_context`); por
  eso `data/navigation.js` se hará con la cuenta (7b), que es quien enlaza.
- Pruebas: `test_margins_api.py`, `tests/e2e/test_margenes.py` y el recorrido
  «Cuenta → comparativa → regresar» (el snapshot solo cambia el ícono ↗).

## Fase 7b: alcance de la cuenta (servidor hecho; frontend no migrado)

> **Estado real:** los módulos de `frontend/` que esta sección menciona
> (páginas `pages/…`, `ui/detail-dialog`, `ui/agreements`, `data/navigation.js`,
> `lib/account-metrics`…) se retiraron el 22/10/2026 al volver al diseño
> anterior; sobreviven el servicio, la API y las pruebas de la API.

- Hecho: `/cuenta/` (y su bloque de consumos) devuelve 404 para una cuenta fuera
  del alcance y 403 sin `view_operations` ni `view_agreements`;
  `cuenta/financiera/` exige `view_costs` y alcance. Ya no hay xfail de acceso.
- Hecho: `data/navigation.js` (`withReturn`) con pruebas; la comparativa lo usa.
- Hecho: la página de la cuenta es `pages/cuenta` con API propia
  (`screens/cuenta/`, `/consumos/`, `/finanzas/`): indicadores, gráficas,
  alertas, tabla, ventanas «Ver más» (`ui/detail-dialog`, `ui/filtered-table`),
  finanzas (solo con `view_costs`), horas de Clockify por lotes y acuerdos
  (`ui/agreements`, sobre `/api/v1/agreements/`). Los totales de pantalla se
  calculan en `lib/account-metrics.js` porque las horas llegan por lotes.
  Se retiraron la plantilla, la vista y el endpoint financiero anteriores.
- Diferencias menores respecto a la anterior: una alerta de consumo exige
  presupuesto mayor que cero; la distribución del consumo en la ventana de
  presupuesto es una lista (sin dona).
- Pendiente: `/api/rpc/obtenerVistaCuentaBeecker` sigue entregando cualquier
  cuenta a quien tenga sesión; desaparece con la fase 10.

## Fase 7c: Delivery Manager (API hecha; frontend no migrado)

> **Estado real:** los módulos de `frontend/` que esta sección menciona
> (páginas `pages/…`, `ui/detail-dialog`, `ui/agreements`, `data/navigation.js`,
> `lib/account-metrics`…) se retiraron el 22/10/2026 al volver al diseño
> anterior; sobreviven el servicio, la API y las pruebas de la API.

- `GET /api/v1/screens/delivery-managers/<slug>/?bloque=base|inv|horas`
  (`view_operations`): primero proyectos y estados; la inversión de Clockify y
  las horas por mes llegan en consultas aparte, y mientras faltan su estado es
  `pending` con cifras vacías (nunca cero).
- Alcance: el DM, sus totales, la inversión y las horas se calculan solo con
  los proyectos de las cuentas visibles; sin ninguno, el DM no existe (404).
  Cada alcance limitado guarda su propio corte en caché.
- Página `pages/delivery-manager` (resumen, tabla, gráfica de horas, detalle
  con CSV que neutraliza fórmulas: `lib/hours-report.js`, con pruebas). Se
  retiraron la plantilla y la vista anteriores; `warm_cache` usa `dm_state`.
- Diferencia: si las fuentes no responden y no hay a quién mostrar, la API da
  502 y la página lo dice; antes redirigía a Operativa.

## Fase 8: Business Overview, glosario y KPIs de DMs (API hecha; frontend no migrado)

> **Estado real:** los módulos de `frontend/` que esta sección menciona
> (páginas `pages/…`, `ui/detail-dialog`, `ui/agreements`, `data/navigation.js`,
> `lib/account-metrics`…) se retiraron el 22/10/2026 al volver al diseño
> anterior; sobreviven el servicio, la API y las pruebas de la API.

> Nota: Business Overview, diccionario y KPIs de DMs conservan su plantilla
> anterior. El Business Overview incrusta los cortes ya recortados al alcance
> (`scoped_snapshots`); el resto de lo descrito sigue vigente en la API.


- **8a.** `data_dictionary.GLOSSARY` declara el glosario corto junto a
  `CONCEPTS` (cada término cita su concepto); `reference/glossary` entrega
  ambos y el diccionario es `pages/diccionario`. «Fuentes y cálculo» de las
  tarjetas sale del mismo diccionario: se acabó la tercera copia. Una prueba
  avisa si un concepto citado desaparece.
- **8b.** `screens/executive/` (`view_executive`): cifras de empresa solo con
  alcance total; el listado de cuentas se recorta al alcance; un bloque que
  falta es `null`. Ya no se incrusta el snapshot completo en la página (cerró
  la fuga de facturación y oportunidades de todas las cuentas).
- **8c.** `pages/executive`: selector de periodo (`ui/period-picker`, con
  `lib/date-range`), tarjetas, rentabilidad mensual (`lib/monthly-model` +
  `ui/monthly-chart`), comparación de cuentas (`lib/ranking`, con el estado en
  la URL) y acuerdos de todas las cuentas (`ui/agreements`). Se retiraron la
  vista, 4 plantillas, 6 scripts y 5 hojas de estilo anteriores. El trabajo de
  preparación del corte ya no renderiza la página.
- **8d.** `screens/kpis-dm/` y `pages/kpis-dm`: T y C sin redondear, gráfica de
  C (`lib/kpi-chart`) y selector `ui/period-filter` (reutilizable por
  Facturabilidad). **Desviación del plan:** con alcance limitado la pantalla
  responde 403 en lugar de recortar filas; los cortes agregan a todo el equipo.
- Se conservan `ejecutiva/actualizacion/` y `executive_numbers.js` hasta migrar
  Costos, Todas las cuentas y Comercial (fase 9).

## Fase 9: permisos, alcance y APIs del resto de pantallas (frontend no migrado)

- `require_capability(code, whole_portfolio=True)`: con los accesos encendidos
  pide la capacidad y, si la pantalla muestra cifras de todo el portafolio o del
  equipo, rechaza (403) a quien tenga alcance limitado sin tocar las fuentes.
  Se aplicó a EVA 1-3 y sus cerrados, Inversión, Facturabilidad (4 pestañas),
  Capacidad (detalle, instalada y CSV), Comercial, Todas las cuentas y los
  endpoints JSON del Business Overview.
- `costos_detalle` pide `view_costs` (cuenta ajena 404; el listado completo,
  403 con alcance limitado); `proyecto` y `proyecto_detalle` piden
  `view_operations` y un proyecto de otra cuenta responde 404.
- `trust(request)` marca las peticiones internas del calentamiento de cache.
- No cambia ninguna pantalla: con `ACCESS_ENFORCED` apagado todo funciona igual.
- Se conserva «Horas por mes» de la cuenta (`pages/account_hours`, API
  `screens/cuenta/horas/`, `docs/reporte-horas-mensuales.md`) con su enlace en
  `cuenta.html` y su regreso; usa `views.authorized_account`.
- APIs de Operativa (`apps/portal/api/operations.py`, mismo permiso y alcance
  total): `screens/eva-1/`, `eva-2/`, `eva-3/`, `inversion/`, `capacidad/` y
  `facturabilidad/` (+ `especialidad/` y `recurso/`). Reutilizan las funciones de
  datos de las vistas (`eva2_data`, `facturabilidad_data`…), que ahora también
  arman las pantallas, y entregan los campos de `schemas.py` con `plain()`.
  Costos y Comercial ya tienen JSON (`ejecutiva/costos/`, `comercial_ejecutiva`,
  `screens/margenes/`), protegidos por capacidad y alcance.
- Pendiente de la 9: retirar `executive_numbers.js` y `ejecutiva/actualizacion/`
  cuando Costos, Todas las cuentas y Comercial dejen de usarlos.

## Fase 10: `/api/rpc/` con permisos (hecha); `proyecto_detalle` sin migrar

- `apps/access/rpc_policy.py` clasifica las 190 funciones del RPC: lectura
  (`view_operations`), escritura (`edit_operations`), configuración
  (`manage_integrations`) y las de cuenta con alcance. Se agregaron dos
  capacidades al catálogo (migración `access.0002`). Con alcance limitado solo
  funcionan las de cuenta; una función sin política se rechaza.
- `proyecto_detalle.js` (≈ 1 MB, 100+ llamadas RPC) **no se reescribe**: por la
  regla de diseño conserva su pantalla y sus llamadas; el RPC ya valida quién
  puede hacerlas. Retirar el RPC requiere una API por llamada y es trabajo
  aparte. Un proyecto de otra cuenta ya responde 404 en la página.

## Fase 11: limpieza (pendiente; solo se retiraron cuatro endpoints)

Estado a 22/10/2026, comprobado en el código:

- **CSP obligatoria: no es posible todavía** (y hoy ni siquiera hay política por defecto). 23 plantillas anteriores llevan
  scripts y estilos en línea (Business Overview 63 `style=`, Comercial 4 scripts,
  Capacidad 22 estilos…) más los bloques `{% block css %}`. Con la política en
  modo de bloqueo se rompen. Por defecto no hay política y el reporte solo se enciende con
  `CSP_REPORT_ONLY=1`; seguirá así hasta que esas pantallas pasen a
  `frontend/` con el diseño igualado (ver la regla de diseño).
- **`ACCESS_ENFORCED=1`: listo para encender, decisión de despliegue.** Todas las
  pantallas y el RPC ya validan capacidad y alcance. Antes: `python manage.py
  access_setup --incluir-usuarios` (migrar `access.0002` primero) y probar con
  una persona de alcance limitado. Ver `docs/permisos.md`.
- **Endpoints sin consumidor: retirados** (23/10/2026): `comercial_ejecutiva`,
  `operaciones_ejecutiva`, `rentabilidad_mensual` y `cuentas_rentabilidad`; nada
  del código los llamaba.
- **Se conservan** `ejecutiva/actualizacion/` y `executive_numbers.js` porque
  Costos, Todas las cuentas, Comercial y la barra de «corte anterior» los usan, y
  `eva4_anterior` hasta el 3/11/2026 (`ANTERIOR_HASTA`).

## Fases siguientes con lo nuevo integrado

- **7. Cuenta y Delivery Manager**: flujos «DM → proyecto → regresar» y
  «Cuenta → comparativa de márgenes → regresar». `data/navigation.js` reemplaza
  a `return_navigation.js` y conserva periodo, `volver` y los parámetros de la
  comparación. La comparativa expone `sold_cost_rate` pendiente. La cuenta y la
  comparativa validan el alcance (hoy una cuenta ajena se abre).
- **8. Business Overview**: API `screens/executive/` con cifras de empresa solo
  para alcance total y listado de cuentas recortado; sin snapshot incrustado;
  comparación de cuentas como `ui/account-ranking`; glosario y diccionario
  desde `reference/glossary`; KPIs DMs con `kpi_quarterly` en servicios.
- **9. Resto de pantallas**, de la más simple a la más compleja.
- **10. `proyecto_detalle`** por pestañas (minutas, Azure/RAID, daily,
  recursos, hitos, Gmail); desaparece `/api/rpc/`.
- **11. Limpieza** y encendido de los accesos.

## Pendiente de negocio (no bloquea el código)

1. Florencia: fuente, unidad y asignación de la tarifa de costo vendida.
2. Reunión de KPIs: IDs de los nueve proyectos de septiembre, regla de T y C,
   inclusión de Miguel A. y alias de nombres.
3. Finanzas: si «mitad superior / inferior» es aceptable como lectura de la
   comparación de cuentas o se necesita una clasificación validada.

## Pendiente de Genesis

Ver las preguntas en `docs/permisos.md`: identidad, roles, alcance por cuenta,
auditoría y despliegue.
