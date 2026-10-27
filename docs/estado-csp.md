# CSP: estado (27/10/2026)

**La política ya es obligatoria por defecto** (`CSP_ENFORCE`, activo salvo
`CSP_ENFORCE=0`). Lo que sigue describe la auditoría que lo permitió.

La política ya existe (`core/frontend.py`: `build_policy`, `CspMiddleware`,
`/csp-report/`) y desde el 27/10 se envía como `Content-Security-Policy` (excepto en
`/admin/` y `/static/`). `CSP_ENFORCE=0` la apaga sin tocar código;
Para solo anotar se necesitan `CSP_ENFORCE=0` y `CSP_REPORT_ONLY=1` juntos;
si `CSP_ENFORCE=1`, el bloqueo tiene prioridad. En pruebas queda apagada
(`config/settings/test.py`) y se aplica donde la prueba lo pide.

## Auditoría hecha

`E2E_CSP=1 pytest tests/e2e ...` corre cada prueba de navegador con la
política aplicada de verdad y anota cada aviso en `tmp/csp-violations.log`
(prueba, página y texto). Primera pasada completa: 644 aprobadas, 795
fallidas en 1 h 20 min.

- **Sin avisos** en Business Overview, Operativa, Costos, Márgenes, Cuenta,
  Horas por mes, EVA, Facturabilidad, Capacidad, Comercial, Diccionario,
  Inversión, KPIs y Todas las cuentas.
- **Avisos solo en las pruebas del detalle de proyecto** (52 archivos). Casi
  seguro vienen de la página de referencia anterior (`?vista=anterior`, HTML
  con estilos y scripts en línea), no de la nueva. No está confirmado: esa
  primera pasada no guardaba la dirección de cada aviso.
- Muchas "fallidas" son esperables: comparan la página nueva con la anterior
  y esta pierde sus estilos en línea, o Playwright usa `wait_for_function`
  con una cadena (necesita `eval`, que la CSP prohíbe). No son fallas de la
  aplicación.

## Segunda pasada (terminada)

Los 52 archivos del detalle de proyecto con la dirección de cada aviso
(1 h 15 min; 251 aprobadas, 792 fallidas por comparar contra la referencia):

- 90,249 avisos en total. **90,224 (99.97 %) vienen de la página anterior**
  (`?vista=anterior`). Desaparecen al retirar `tests/reference`.
- **25 avisos en la página nueva** (`/proyectos/AMK.008/`), todos «script en
  línea» en tres pruebas: `test_project_compatibility_start`,
  `test_generic_timeline` y `test_ixs_ai_sources`. Esas pruebas inyectan el JS
  original con `load_project_reference` (herramienta de pruebas), así que no
  son código de la aplicación.
- Conclusión: **ninguna violación atribuible al código de la aplicación**.
  Nada que corregir antes de activar la política.

## Pendiente, en orden

1. (Hecho) Auditoría del detalle de proyecto: sin violaciones propias.
2. (Hecho) Política obligatoria por defecto con prueba de la cabecera
   (`tests/core/test_frontend_support.py`) y carga real de seis pantallas bajo
   la cabecera (`tests/e2e/test_csp_enforced.py`).
3. (Con la suite completa del 27/10) Suite en verde.

## Otros pendientes de la fase 11

- (Hecho 27/10) `/api/rpc/` ya no está en `config/urls.py`: solo lo monta
  `tests/reference/urls.py`, junto con `gas_shim.js` (movido a
  `tests/reference/static/core/js/`). Una prueba comprueba el 404 en rutas
  reales.
- Más adelante: congelar las comparaciones y borrar `tests/reference`, el RPC y
  su política (ver `docs/retiro-detalle-anterior.md`).
