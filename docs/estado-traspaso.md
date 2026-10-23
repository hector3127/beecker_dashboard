# Estado de traspaso de la migración (24/10/2026)

Lee primero `AGENTS.md` y `docs/plan-migracion-frontend.md`.

## Última pantalla terminada
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

Falta en Inversión:
1. Una diferencia de alto: la tarjeta «Por especialidad» mide ~15 px menos que la anterior (`two` 249 contra 263). Comparar `h2`, `.hs` y el pie `tfoot`, que probablemente tienen otro relleno por `components.css`.
2. Prueba e2e `tests/e2e/test_inversion.py` (estructura, cambio de mes que recarga con `?mes=`, barras con ancho, regreso a Operativa).
3. Correr la suite, comitear y actualizar el plan.

## Pruebas
- Última corrida completa (antes de Inversión): `pytest tests/portal tests/core tests/access tests/e2e` → 1044 pasaron, 1 omitida; `ruff check` limpio.
- node (`node --test tests/frontend/*.test.*`): 3 fallos que ya existían, del JS anterior (`executive_report`, `executive_numbers`/Comercial y `cost_sprint_details`); se retiran en la limpieza.
- Inversión: solo comparación de estilos contra la anterior (formulario y celdas iguales; queda la diferencia de alto). Todavía no se ha corrido pytest con ella.

## Siguiente paso concreto
Cerrar Inversión (puntos 1 a 3), y seguir el bloque 3 en este orden: Capacidad (instalada y detalle), Facturabilidad (general, especialidad, recurso), Facturabilidad por área, EVA 1, 2 y 3. Después: detalle del proyecto por pestañas y la limpieza final (borrar plantillas, CSS y JS anteriores y las pruebas con `?vista=anterior`; CSP).

## Temporales (no comitear; borrar al terminar)
`shots_tmp/`, `tests/e2e/test_zz_*.py`, el worktree `../bd_op`. Copias versionadas de las herramientas en `tools/migracion/`.
