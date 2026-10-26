# Fase 11: retiro de la presentación anterior de Oportunidades financieras

26/10/2026. Se retiran `portal/oportunidades_financieras.html`, su CSS y su
JS (`opportunity_profitability.css`, `opportunity_details.js`), la vista
`views.oportunidades_financieras` y el parámetro `?vista=anterior` de
`/ejecutiva/oportunidades/`, que ya solo sirve `pages/margins.html` con datos
por API. `views.costos_detalle` deja de desviar a esa vista: el desvío a
márgenes lo hace `pages.costs`. No se tocan cifras, fuentes ni permisos.

Tres pruebas se retiran porque solo comprobaban la presentación anterior y
contradecían el diseño vigente (que ya no muestra «Tarifa de costo vendida»,
cubierto por `test_sold_cost_rate_column_is_removed`): la vista anterior con
margen vendido/real, el desvío de costos a la jerarquía y la columna de tarifa
pendiente. Las cifras siguen cubiertas por `tests/portal/test_margins_api.py`,
los servicios de `opportunity_profitability` y `tests/e2e/test_margenes.py`.

Verificación: 1760 pruebas de portal, core, márgenes, costos, ejecutiva y
todas las cuentas aprobadas; ruff aprobado.
