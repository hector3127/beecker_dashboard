# Fase 11: la aplicación ya no incluye el detalle de proyecto anterior

26/10/2026. `apps/portal/static/portal/` (CSS, JS, imágenes, vendor) y
`apps/portal/templates/portal/` (`base.html`, `proyecto_detalle.html`) se
movieron a `tests/reference/{static,templates}/portal/`. La aplicación ya no
los sirve: `pages.project_detail` renderiza solo `pages/project_detail.html`
(con los mismos permisos y la cookie CSRF), `views.proyecto_detalle`,
`pages._modern`, `anterior_disponible()` y `ANTERIOR_HASTA` desaparecen y
`?vista=anterior` ya no hace nada en producción.

## Referencia para pruebas

Las comparaciones con el original se conservan sin pasar por la app:

- `tests/reference/views.py` y `urls.py` entregan el detalle anterior en
  `/proyectos/<id>/?vista=anterior` solo cuando una prueba pide la fixture
  `reference_site` (`tests/conftest.py`; en `tests/e2e` es automática).
  Agrega a `ROOT_URLCONF`, `TEMPLATES` y `STATICFILES_DIRS` las rutas de
  `tests/reference`. Por eso las pruebas de navegador no cambiaron de URL.
- Las pruebas Node y `tests/e2e/project_reference.py` leen
  `tests/reference/static/portal/js/proyecto_detalle.js`.
- `gas_shim.js` y `/api/rpc/` siguen existiendo porque esa referencia los usa.

## Qué falta para borrar la referencia

Congelar como valores esperados lo que hoy comparan unas 45 pruebas Node y
unas 30 de navegador con el original; después se eliminan `tests/reference`,
`core/static/core/js/gas_shim.js`, `core/rpc/` y `access/rpc_policy.py`.

## Verificación

Node: 472 aprobadas. Pruebas de entrada, comparación anterior, ejecutivo AER/IXS,
API del detalle, navegación de regreso y core: 241 aprobadas. `manage.py check`
y `collectstatic` sin avisos; ruff y mypy de pages.py aprobados. La suite
completa se corre al final del bloque.
