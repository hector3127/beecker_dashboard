# Estado de traspaso de la migración (24/10/2026)

Lee primero `AGENTS.md` y `docs/plan-migracion-frontend.md`.

## Última pantalla terminada
- **Facturabilidad por área** (`pages/billability_area.html`): General,
  Detalle recurso, KPIs, % Recurso y Detalle HRS. Datos mediante API v1;
  módulos separados, DOM seguro y CSS externo. Se conservan los servicios
  originales de GSE, deduplicación, lotes, caché, fuentes, errores por mes,
  festivos, jornadas, filtros, bandas/bajas, paginación y exportaciones.
  Pruebas de API: 41 aprobadas. Dos pruebas Node comparan el modelo con
  el JS anterior. Comparación visual a 1450 y 390 px de los cinco apartados
  y de un área seleccionada, con texto idéntico en las tablas.
  Veinte pruebas e2e aprobadas; regresión completa: **1160 aprobadas,
  1 omitida**. JavaScript: **120 aprobadas y los mismos tres fallos
  anteriores** del código sin migrar. Ruff, formato, mypy y comprobación
  de Django aprobados. La prueba anterior que exigía el shim ahora verifica
  tanto la ruta activa modular como `?vista=anterior`, sin perder controles
  de año, navegación, cookie CSRF ni enlaces.
  **Siguiente: EVA 1–3 y sus cerrados.**
- **Facturabilidad general, especialidad y recurso**: plantillas
  `pages/billability*.html`, CSS y JS separados, con el mismo contexto
  Python y los mismos permisos. Selector de periodo compartido, sin
  scripts ni estilos en línea en las plantillas. Doce pruebas e2e de
  cifras, filtros, navegación, errores y comparación visual a 1450 y
  390 px (selectores abiertos y cerrados); doce pruebas de servidor.
  Las anteriores siguen disponibles con `?vista=anterior`.
  La vista por área se completó después, como se indica arriba.
- **Capacidad: detalle diario** (`/capacidad-instalada/`):
  `pages/capacity_daily.html`, CSS separado y módulos `model.js`, `view.js`,
  `main.js`. API `screens/capacidad/diaria/` y `.../proyecto/`, sin shim RPC
  en el frontend activo. Se conservaron filtros, matriz, recursos, paginación,
  CSV, concurrencia de dos proyectos y reglas de horas. Comparación visual
  a 1450 y 390 px de matriz y recursos; nueve pruebas e2e y trece de API.
- **Capacidad: asignaciones mensuales** (`/operativa/capacidad-instalada/`):
  `pages/capacity.html`, CSS y JS separados; filtros GET y CSV sin cambiar.
  Tres pruebas e2e aprobadas (filtros/exportación y comparación visual a 1450
  y 390 px). El detalle diario también se completó después.
- **Inversión** completada en `0028959` con cinco pruebas e2e.
- **Costos** (`/ejecutiva/costos/detalle/?vista=proyectos`), commit `5c945dc`.
- Antes, con commit cada una: Comercial `a8239ca`, Todas las cuentas `b314f35`, Business Overview `dca99b5`, KPIs de DMs `b02e623`, diccionario `cf702aa`, cuenta `5277a21`, Delivery Manager `56d169e`, márgenes `8f53c08`, EVA-04 `8d50bb0`, Operativa `ca4434d`.
- `AGENTS.md` y `tools/migracion/`: `86c69d0`.

## Inversión completada al retomar

Se conservaron y completaron los cambios pendientes descritos abajo.
La diferencia de alto era el margen superior de un encabezado anulado por
`.ds .card h2`; se corrigió su prioridad sin modificar el diseño anterior.
`tests/e2e/test_inversion.py`: cinco pruebas aprobadas usando Chrome instalado
(`--browser-channel chrome`); compara estilos y cajas a 1450, 900 y 390 px,
además de datos, cambio de mes, barras, regreso y error de fuente.
Capturas: `tmp/migration/investment/<ancho>/previous.png` y `current.png`.
Los cálculos y las fuentes no cambiaron. El siguiente bloque es Capacidad.

### Cambios recibidos de Claude (registro histórico)

Inversión (`/operativa/inversion/`), inicialmente sin commitear:
Sin commitear (en el árbol de trabajo):
- `frontend/templates/pages/investment.html`, `frontend/static/styles/pages/investment.css`, `frontend/static/scripts/pages/investment/main.js`.
- `apps/portal/pages.py` (vista `investment`), `apps/portal/urls.py` (ruta), `apps/portal/views.py` (`inversion` usa `render_page`).
- `tools/migracion/migrate_page.py` e `inline2css.py` (ajustes: quita el `<main class="page">` anterior, cambia el include del encabezado y genera estilos `.x.x`).

Pendientes recibidos de Inversión (ya resueltos; referencia histórica):
1. Una diferencia de alto: la tarjeta «Por especialidad» mide ~15 px menos que la anterior (`two` 249 contra 263). Comparar `h2`, `.hs` y el pie `tfoot`, que probablemente tienen otro relleno por `components.css`.
2. Prueba e2e `tests/e2e/test_inversion.py` (estructura, cambio de mes que recarga con `?mes=`, barras con ancho, regreso a Operativa).
3. Correr la suite, comitear y actualizar el plan.

## Pruebas recibidas de Claude (referencia histórica)
- Última corrida completa (antes de Inversión): `pytest tests/portal tests/core tests/access tests/e2e` → 1044 pasaron, 1 omitida; `ruff check` limpio.
- node (`node --test tests/frontend/*.test.*`): 3 fallos que ya existían, del JS anterior (`executive_report`, `executive_numbers`/Comercial y `cost_sprint_details`); se retiran en la limpieza.
- Inversión: solo comparación de estilos contra la anterior (formulario y celdas iguales; queda la diferencia de alto). Todavía no se ha corrido pytest con ella.

## Siguiente paso concreto
Migrar EVA 1–3 con sus cerrados. Facturabilidad completa ya usa `frontend/`.
El área lee `screens/facturabilidad/area/` y conserva sus cinco apartados.
Las pruebas comparan con `?vista=anterior`; las capturas se generan bajo
`tmp/migration/billability_area/`. El CSS anterior oculta la navegación de
apartados en móvil: se conservó y documentó, sin dar por probada una navegación
que ya no estaba disponible. Después: Proyecto,
detalle del proyecto por pestañas y limpieza.

## Publicación
- Se verificó `origin/main` y se publicó mediante push normal el rango
  `45c93bf..9e93e52` (17 commits), con autorización explícita del usuario.
- El detalle diario se completó y validó después, en un commit separado;
  publicación mediante push normal, manteniendo los pendientes ajenos fuera.

## Verificación al retomar con Codex
- Último bloque, Facturabilidad por área: **1160 aprobadas, 1 omitida**
  en la regresión completa; veinte pruebas e2e de esta pantalla y 41 de API.
  JavaScript: 120 aprobadas y tres fallos anteriores documentados. Los dos
  contrastes nuevos del modelo pasan. Los pendientes de Claude siguen fuera
  del commit, sin cambios.
- Facturabilidad: comparación visual y funcional de las tres vistas
  completada (`tests/e2e/test_facturabilidad.py`: 12 aprobadas).
  Validación de servidor: `tests/portal/test_billability_pages.py` y
  `test_views.py`: 68 aprobadas. Ruff, formato, mypy y revisión de Django
  aprobados. JavaScript conserva 118 aprobadas y los tres fallos anteriores.
- Regresión completa después de esas tres vistas: **1098 aprobadas,
  1 omitida**, con Chrome y los cuatro temporales excluidos. Se conservaron
  los pendientes de Claude sin modificarlos ni incluirlos en los commits.
- Última suite, tras detalle diario: **1074 aprobadas, 1 omitida**, con Chrome
  instalado y los mismos cuatro temporales excluidos. `ruff check`, formato,
  `mypy` de páginas/API y `manage.py check` aprobados.
- JavaScript actual: **118 aprobadas, 3 fallidas**. Las tres fallidas siguen
  siendo las del código anterior, sin cambios en sus archivos. Las tres
  pruebas nuevas del modelo diario pasan y contrastan sus resultados con el
  modelo anterior.
- En la primera regresión del detalle diario hubo una falla intermitente en
  `test_person_with_edit_changes_a_status_and_it_is_saved` (Acuerdos, HTTP
  403). Sus tres pruebas aisladas pasaron y la repetición completa pasó.
  No se modificaron la prueba, sus permisos ni el código de Acuerdos.
- Suite tras Inversión: **1049 aprobadas, 1 omitida** (Chrome instalado,
  `--browser-channel chrome --no-cov`; se excluyen los cuatro `test_zz_*`
  temporales recibidos).
- Suite final tras Capacidad mensual: **1052 aprobadas, 1 omitida** con el
  mismo comando. `ruff check` y `mypy apps/portal/pages.py` aprobados.
- JavaScript: **115 aprobadas y 3 fallidas**, las ya documentadas del código
  anterior: `cost_sprint_details.test.cjs`, `executive_report.test.cjs` y
  `financial.test.cjs`. No se modificaron sus archivos ni sus reglas.
- La prueba de cambio de mes de Inversión emite un único evento: Playwright
  ya genera `change` al rellenar un campo `month`; duplicarlo ocasionaba una
  carrera de navegación en la suite completa.
- Se usa Chrome instalado porque no está descargado el Chromium de Playwright.
- Comparación visual reproducible: `tests/e2e/test_inversion.py` y
  `tests/e2e/test_capacidad.py`; capturas bajo `tmp/migration/`.
- Se preservaron sin modificar los cambios recibidos de las herramientas
  `inline2css.py` y `migrate_page.py`, además de los temporales de Claude.

## Temporales (no comitear; borrar al terminar)
`shots_tmp/`, `tests/e2e/test_zz_*.py`, el worktree `../bd_op`. Copias versionadas de las herramientas en `tools/migracion/`.
