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
| 10 | `proyecto_detalle` y fin de `/api/rpc/` | API v1 para los bloques migrados, Cliente, Centro de Comunicación y operaciones de Acciones; resto RPC | **Parcial**: ambos Ejecutivos y Cliente; Esfuerzo, Recursos, Planeación, RAID, Azure, IA y Comunicación IXS usan módulos. Acciones tiene modelo/operaciones separados; falta su vista/formularios, otras pestañas AER y estructura compartida | **Parcial**, no completada |
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

Terminados: ambos Ejecutivos y Cliente de ambas familias; Esfuerzo, Recursos,
Gestión RAID, Azure DevOps, IA y Centro de Comunicación IXB/SaaS/RaaS.
También están separados el editor de hitos históricos y la ventana de
comunicados (incluida extensión); ver el traspaso para su evidencia y alcance.
La entrada modular ya usa API para filtros y dashboards, pero el encabezado
y la navegación entre pestañas todavía dependen del script anterior.

| Familia | Apartados que faltan por modularizar y validar |
|---|---|
| IXB/SaaS/RaaS | Vista, filtros y formularios de Acciones; modelo y operaciones ya separados |
| AER/T&M | Planeación, Esfuerzo, Riesgos, Recursos e IA; vista/formularios de Acciones compartidos con IXS |
| Compartido | Encabezados, pestañas, entrada/estado y auxiliares de Planeación; retirar dependencia de `proyecto_detalle.js` y del shim RPC en la ruta nueva |

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
Planeación conserva puentes y auxiliares en el archivo anterior, entre ellos
`ixsEditarHitoTimeline`, `_ixsCargarEstadosRecursos` y `_ixeAuto`; extraerlos en
la integración compartida, sin confundirlos con volver a migrar su vista y editores.
El retiro de archivos anteriores del repositorio y la CSP obligatoria
pertenecen a la fase 11, posterior a completar este detalle.

### Revisión de avances de Claude y operaciones de Acciones AER/IXS

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

**Acciones y fase 10 siguen parciales:** falta separar su vista, filtro de
tabla y ambos formularios, que siguen en el script anterior con eventos en
línea. Después pestañas AER y estructura compartida. No retirar el shim ni
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
