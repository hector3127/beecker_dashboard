# CSP: dónde se quedó (26/10/2026, noche)

La política ya existe (`core/frontend.py`: `build_policy`, `CspMiddleware`,
`/csp-report/`) y sigue **apagada por defecto** (`CSP_REPORT_ONLY=0`).

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

## Pendiente, en orden

1. Repetir la auditoría solo con los 52 archivos del detalle de proyecto (ya
   guarda la dirección de cada aviso):
   `E2E_CSP=1 pytest <archivos> -q --no-cov` y revisar
   `cut -f2,3 tmp/csp-violations.log`. Descartar las filas con
   `vista=anterior`; lo que quede es de la página nueva y se corrige.
2. Hacer la política obligatoria por defecto (`CSP_REPORT_ONLY` → cabecera
   `Content-Security-Policy`) y una prueba que compruebe la cabecera.
3. Suite completa en verde.

## Otros pendientes de la fase 11

- Opción A recomendada: sacar `/api/rpc/` de `config/urls.py` y dejarlo solo
  en `tests/reference/urls.py` (con `gas_shim.js`).
- Más adelante: congelar las comparaciones y borrar `tests/reference`, el RPC y
  su política (ver `docs/retiro-detalle-anterior.md`).
