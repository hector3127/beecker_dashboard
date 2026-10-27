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
- `/api/rpc/` y `gas_shim.js` ya no se publican (27/10): `tests/reference/urls.py`
  monta el RPC y `tests/reference/static/core/js/gas_shim.js` lo sirve, solo
  para esas comparaciones. La reference_site es automática en toda la suite.

## Qué falta para borrar la referencia

Congelar como valores esperados las comparaciones Node y de navegador con el
original. Al 27/10 main conserva 41 archivos Node que leen ese script. El
piloto aer_executive está en `4103ed6`, rama local `congelar-referencias`,
todavía fuera de main. Después se podrán retirar tests/reference y los
generadores sin consumidores. El shim ya está dentro de tests/reference.

No eliminar `core/rpc/` en bloque: `warm_cache` usa get_rpc_function y varios
módulos registran funciones internas. Separar el transporte HTTP/política de
referencia del registro/servicios todavía usados antes de decidir su retiro.

## Verificación

Node: 472 aprobadas. Pruebas de entrada, comparación anterior, ejecutivo AER/IXS,
API del detalle, navegación de regreso y core: 241 aprobadas. `manage.py check`
y `collectstatic` sin avisos; ruff y mypy de pages.py aprobados. La suite
completa se corre al final del bloque.
