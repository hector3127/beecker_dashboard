# Entrada a fase 11 (26/10/2026)

La fase 10 sigue cerrada. El usuario autorizó integrar los cambios nuevos y
preparar la fase 11. Este bloque valida la integración; no elimina todavía
referencias ni activa una política de bloqueo global. Ese párrafo describe
la preparación previa; el primer retiro ya se completó en el bloque siguiente.

## Primer bloque de limpieza completado: EVA-04

- Retiradas la vista `views.eva4`, la plantilla `portal/eva4_anterior.html`
  y la bifurcación de `pages.eva4`. La ruta actual, sus servicios, cálculos,
  permisos y estilos se conservan. No quedan referencias a esos dos nombres
  en código/pruebas vigentes.
- `vista=anterior` ahora entrega la plantilla modular incluso antes del corte
  anterior; conserva `mes` y sigue sin consultar fuentes en la carga HTML.
  Pruebas antiguas sustituidas por verificaciones de ese contrato.
- Antes del retiro se ejecutó la referencia visual vigente con reloj fijo;
  después se repitió con CSP de bloqueo solo en el navegador. Las imágenes
  son idénticas píxel a píxel a 1450/900/390 px. Ejemplo SHA256 escritorio:
  `c29364cc9bbf6dc787f1b13406bfd0435fc944f8d637db99875535df3af6c115`.
  Las copias locales están en `tmp/fase11/eva4-before/` y
  `tmp/design/eva4-reference/`. El rediseño posterior a fase 10 es la referencia.
- 93 pruebas dirigidas de servidor aprobadas: `test_eva4.py`,
  `test_eva4_api.py`, `test_eva4_hours.py` en `tests/portal/` y
  `tests/core/test_frontend_support.py`. Una expectativa residual de servir
  la plantilla retirada falló en la primera corrida; se actualizó al contrato
  nuevo y se repitieron los cuatro archivos completos, sin omisiones.
- Revisión ampliada final: `pytest tests/portal tests/core tests/access -q
  --no-cov --tb=short`, **1682 aprobadas** en 94 s. Incluye las pruebas
  dirigidas anteriores, sin sumarlas dos veces; no es la suite general e2e.
- 38 Chrome aprobadas: `tests/e2e/test_eva4.py` y `test_page_capture.py`.
  Incluyen estructura con/sin parámetro obsoleto, filtros/paginación y CSV
  bajo CSP real, permisos limitados, errores/reintento y navegación de regreso.
  La captura real se probó sin bloqueo CSP; su certificación sigue pendiente.
- 498 Node, Ruff/formato de `apps core tests` y mypy de páginas aprobados.
- Nuevo fixture reutilizable `enforced_csp`: aplica la cabecera de bloqueo
  exclusivamente a documentos locales del navegador de pruebas. Sigue sin
  activar CSP global, ACCESS_ENFORCED ni proveedores reales.
- Se conservan el corte compartido y las referencias de las otras pantallas.
  Quedan 32 HTML anteriores en portal; no borrarlos todos ni eliminar sus
  servicios Python por compartir carpeta con las vistas anteriores.

## Segundo bloque: diccionario y captura con CSP

- Retiradas `views.diccionario_datos`, su plantilla y la bifurcación de
  `pages.dictionary`. Se conservan URL/nombre de ruta, definiciones/API,
  login, regreso, búsqueda, categorías y orden. `vista=anterior` abre la
  modular y mantiene `q`. Quedan 31 HTML anteriores en portal.
- Referencia vigente antes/después idéntica píxel a píxel a 1450/900/390 px;
  las posteriores se tomaron con CSP de bloqueo solo en pruebas. Copias en
  `tmp/fase11/dictionary-before/` y `tmp/design/dictionary-reference/`.
  SHA256 escritorio:
  `37ad120db1099085fb472f4e2c9ad3352a04aed981b263d0841a145fed8bc58f`.
- La prueba de captura con html2canvas REAL detectó dos estilos del documento
  clonado bloqueados. La política propuesta permite SOLO sus dos huellas
  SHA256 (`core.frontend.CAPTURE_STYLE_HASHES`): pseudoelementos de html2canvas
  1.4.1 y reglas estáticas de animación/elementos ignorados de page-capture.js.
  No se permite unsafe-inline ni estilo arbitrario; no se modifica vendor.
  Si cambian versión o contenidos, revisar las huellas y repetir la prueba.
- Tras corregir ese fallo diagnóstico, 54 Chrome aprobadas en
  `test_diccionario.py`, `test_page_capture.py`, `test_eva4.py` y
  `test_account_logos.py`. Revalidación del archivo de capturas tras quitar su
  dependencia del corte antiguo: 15 aprobadas (solapan con las 54).
  La biblioteca real se comprueba con política normal y de bloqueo en la guía:
  PNG válido, carga diferida y ausencia de infracciones. No certifica todavía
  la captura de todas las pantallas.
- 498 Node aprobadas; Ruff/formato (707 archivos) y mypy aprobados.
  Pruebas nuevas verifican login y shell sin datos con/sin parámetro obsoleto.
  Las pruebas de captura ya no fuerzan disponibilidad de una versión anterior.
- Revisión ampliada final: `pytest tests/portal tests/core tests/access -q
  --no-cov --tb=short`: 1686 aprobadas en 101 s, sin omisiones ni fallos.
  Incluye las 61 dirigidas iniciales; no sumar como casos distintos.
- CSP global y accesos siguen sin activarse. Continuar otras referencias y
  ampliar CSP real a gráficas, ventanas y capturas representativas.

## Retiro de KPIs de Delivery Managers (base 3c5b2fa)

- Al iniciar este bloque se publicó main hasta `3c5b2fa`, como pidió el
  usuario. La integración de Christian y los cuatro commits protegidos siguen
  conservados. Este retiro es posterior a ese push.
- Retiradas `views.kpis_delivery_managers`, la plantilla `portal/kpis_dm.html`
  y la bifurcación antigua de `pages.kpis_dm`. También se retira el JavaScript
  `portal/js/kpi_chart.js`, sin consumidores de producción restantes.
- No se modifica `kpi_context`, su API/serializador, las fuentes, cortes,
  fórmulas ni redondeos. Las pruebas de contexto/cortes siguen comprobando
  igualdad de datos completos; las de periodo anual usan la API vigente.
  No se borraron las pruebas de agregación para dejar de ejecutarlas.
- Los dos casos Node de escala/selección del script viejo ahora importan
  `renderChart` del módulo activo, sin leer ni ejecutar el archivo anterior.
  Mantienen cero, meses ausentes, más de 100%, resaltado y selección de serie.
- Enlaces guardados con `vista=anterior` sirven la pantalla modular. Nuevas
  pruebas aseguran que no se carga el histórico en el HTML y que ese parámetro
  no evita el alcance de equipo completo. Login/permisos conservados.
- Tres referencias del diseño vigente se capturaron antes y después, en
  1450/900/390 px: idénticas píxel a píxel. Las posteriores usan CSP real
  únicamente en el navegador de prueba. Imágenes locales ignoradas en
  `tmp/fase11/kpis-before/` y `tmp/design/kpis-reference/`.
- 78 pruebas dirigidas de servidor aprobadas. 505 Node aprobadas.
  Revisión amplia posterior: 1693 aprobadas con
  `pytest tests/portal tests/core tests/access tests/capacidad/test_history_range.py
  -q --no-cov --tb=short` (85 s, sin omisiones). Incluye las 78 dirigidas.
  40 Chrome aprobadas en `test_kpis_dm.py`, `test_facturabilidad.py` y
  `test_page_capture.py`; revalidación posterior de KPIs completo: 10 aprobadas
  (las nueve anteriores + un caso nuevo de histórico ausente). No sumar las
  dos corridas como 50 casos distintos.
- La primera corrida de navegador dio 39 aprobadas y un fallo de sincronía
  en el selector anual de Facturabilidad general. Se amplió la espera de la
  prueba a red local en reposo, antes de usar cada selector; antes solo se
  esperaba el montaje de la tabla de Recurso. La repetición de los tres
  archivos completos pasó, sin omitir ni marcar el caso como esperado.
- Ruff/formato y mypy pasan. Quedan 30 HTML anteriores y 36 estáticos en
  portal: continuar por pantalla, sin borrar servicios JSON ni CSS compartido
  en bloque. Fase 11 continúa; CSP global y accesos no se activan.

## Integración revisada

- Base revisada: `24cd3cf` (diseño/logos) y `834bbfa` (fechas de Capacidad).
  Se conserva el diseño nuevo solicitado; no se exige volver al diseño previo
  a esos commits. Las comparaciones históricas siguen disponibles.
- Aplicada localmente `portal.0003_account_logo`, con respaldo consistente
  previo de SQLite en `tmp/backups/before-account-logo-20261026-123443.sqlite3`.
  La copia y la base están ignoradas por Git. En otros entornos se debe ejecutar
  `python manage.py migrate` antes de usar los logos; el commit no distribuye
  una base ya migrada.
- Tipado de `service_distribution` corregido y tres archivos formateados.
- Restaurado el contrato anterior de rangos MPB repetidos: `resolve()` y
  `resolve_full()` abarcan todas las filas del mismo ID. El commit `48068c0`
  ya usaba ese rango; la integración lo había limitado a la primera fila
  salvo petición explícita de rango completo. Eso afectaba consumidores como
  Proyecto simple y la precarga. La prueba comprueba ambos órdenes de filas.
  No se alteran filtros explícitos de fechas ni fórmulas de horas/costos.
- Se conservan los cambios funcionales del compañero: booking por periodo,
  porcentajes vendidos fraccionarios, meses futuros pendientes y fechas de
  Capacidad desde Histórico con respaldo Azure. No son cambios solo visuales;
  no se revierten durante la limpieza.
- CSP permite `blob:` únicamente en imágenes para las vistas previas locales.
  La prueba de navegador aplica la cabecera de bloqueo a la página de Cuenta
  solo durante ese caso y comprueba que la imagen se decodifica (80 px).
  La configuración normal continúa sin bloqueo y sin activar ACCESS_ENFORCED.

## Evidencia de este bloque

- 388 pruebas de servidor aprobadas: `tests/clockify`, `tests/ejecutivo`,
  `tests/capacidad/test_history_range.py`, y archivos de `tests/portal/`:
  `test_account_hours.py`, `test_account_logos.py`, `test_project_detail_api.py`,
  `test_operativa_api.py`, `test_margins_api.py`, `test_roster.py`,
  `test_facturability.py`; también `tests/core/test_frontend_support.py`.
- 498 Node aprobadas: `node --test tests/frontend/*.test.*`.
- 74 pruebas Chrome aprobadas en `tests/e2e/test_operativa.py`,
  `test_account_logos.py`, `test_project_independence.py`, `test_page_capture.py`
  y `test_facturabilidad.py`.
- Después del ajuste CSP: 15 aprobadas al repetir `tests/e2e/test_account_logos.py`
  completo (4 casos, uno nuevo) y `tests/core/test_frontend_support.py` (11).
  Estos casos se solapan con los anteriores; no sumar como pruebas distintas.
  La primera prueba nueva falló por usar un método incorrecto del objeto
  APIResponse de Playwright; se corrigió a `response.headers` y se repitió
  todo el archivo sin omisiones ni fallos.
- Ruff y formato: aprobados sobre `apps core tests`, excluyendo únicamente
  los diagnósticos ajenos `test_zz_*.py`; 706 archivos formateados correctamente.
  Mypy de `apps/portal/pages.py`, Django check y detección de migraciones:
  aprobados. La advertencia de `staticfiles/` ausente en pruebas sigue presente.
- Editor de logo móvil inspeccionado en
  `tmp/design/logo-upload-reference/editor-390.png`; las pruebas también
  revisan escritorio, persistencia, eliminación y ausencia de desborde móvil.
  No es una nueva validación visual integral de todo el rediseño.

## Orden de trabajo restante

1. **Separar referencias y producto activo.** La búsqueda en plantillas de
   `frontend/` no encuentra referencias a `portal/js`, `portal/css` o `legacy/`.
   El grafo de Proyecto y sus pruebas de red siguen sin script/shim/RPC.
   Aun así hay 33 HTML y 37 archivos estáticos en los directorios anteriores.
   Son inventario, no autorización de borrado masivo: identificar consumidores
   indirectos, plantillas base, pruebas de tokens y referencias visuales.
2. **Retirar rutas de comparación y sus pruebas de forma coordinada.**
   `pages.py` todavía tiene `anterior_disponible()` y `_modern()`; Costos usa
   `anterior=1` y `vista=proyectos` tiene otro significado. Unos 103 archivos de
   pruebas mencionan una ruta/referencia anterior o archivos estáticos anteriores.
   No borrar archivos de prueba completos si también cubren la ruta vigente.
   Mantener sus casos funcionales y sustituir las comparaciones por referencias
   visuales del diseño aprobado antes de retirar los originales.
3. **Conservar los servicios del backend.** Las rutas de actualización,
   acuerdos, ingresos, costos y cuenta financiera en `views.py` devuelven JSON;
   no son pantallas antiguas que puedan borrarse por su ubicación. Varias
   páginas nuevas también reutilizan contexto Python mediante `render_page()`.
   No borrar `views.py`, cálculos, APIs ni CSV en bloque.
4. **Validar CSP completa antes del bloqueo.** El importmap tiene nonce y las
   plantillas nuevas no contienen eventos/estilos HTML en línea. El caso del
   logo queda probado, pero no certifica todas las pantallas. Revisar captura
   global (`ui/page-capture.js` y html2canvas generan estilos en un documento
   clonado), gráficos, ventanas, descargas, fuentes y logos bajo política real.
   Asignar propiedades CSS con `node.style` no prueba por sí solo una infracción;
   medir violaciones en navegador antes de cambiar el diseño o la política.
5. **Cierre.** Repetir suite general, comparaciones visuales del diseño vigente,
   permisos limitados, filtros/CSV/regreso de Horas por mes y red del detalle.
   Documentar evidencia antes de marcar fase 11 terminada. No activar accesos
   Genesis, enviar correo real ni hacer push sin petición expresa.

Los temporales de migración y los cuatro `tests/e2e/test_zz_*.py` siguen ajenos,
sin modificar ni incluir en commits. Añadir archivos siempre por nombre.
