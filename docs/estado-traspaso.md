# Estado de traspaso de la migración (24/10/2026)

Lee primero `AGENTS.md` y `docs/plan-migracion-frontend.md`.

## Última pantalla terminada
- **Capacidad: asignaciones mensuales** (`/operativa/capacidad-instalada/`):
  `pages/capacity.html`, CSS y JS separados; filtros GET y CSV sin cambiar.
  Tres pruebas e2e aprobadas (filtros/exportación y comparación visual a 1450
  y 390 px). El detalle diario `/capacidad-instalada/` todavía no se migró.
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
Migrar el detalle diario de Capacidad (`/capacidad-instalada/`): su JS anterior
genera la interfaz y consulta `capacidadInstaladaBase` y
`capacidadInstaladaDatosProyecto` por RPC. Conservar exactamente las reglas
actuales de horas, filtros, recursos, matriz diaria y CSV al separar módulos
y API. Después: Facturabilidad (general, especialidad, recurso y área), EVA
1–3 con cerrados, Proyecto, detalle del proyecto por pestañas y limpieza.

## Verificación al retomar con Codex
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
