# Fase 11: limpieza por lotes sobre 1e17d99

El usuario pidió acelerar especialmente el retiro de archivos sin uso. Este
bloque agrupa consumidores aislados y elimina árboles que ya no se sirven;
no borra directorios por antigüedad ni elimina servicios Python.

## Resultado: 21 archivos retirados, 1 420 452 bytes

### Tres comparaciones y cuatro huérfanos del portal

- `apps/portal/templates/portal/{inversion,proyecto,todas_cuentas}.html`.
  Las rutas correspondientes usan siempre las plantillas de frontend mediante
  `_current`, conservando el constructor de contexto, login, permisos, filtros,
  cifras y enlaces de regreso. El respaldo de esas tres vistas Python también
  apunta a la plantilla vigente. Los parámetros antiguos son inocuos.
- `apps/portal/templates/portal/{en_ejecucion,suspendidos}.html`.
  Ninguna vista/ruta/include ni prueba vigente las consume. No se eliminan
  los esquemas y servicios de proyectos suspendidos: son datos de Operativa.
- `apps/portal/static/portal/{css/data_dictionary.css,js/data_dictionary.js}`.
  El diccionario antiguo ya se retiró; tampoco quedaban consumidores de estas
  dos hojas/script. El diccionario modular no cambia.

### Árbol de panel original que ya no se renderizaba

- `core/templates/core/index.html` y `core/static/core/css/legacy_skin.css`.
- Los doce HTML de `templates/legacy/`: `CapacidadInstalada`,
  `DailyPanelFrontend`, `GSE`, `css_main`, `js_main`, `snippet_modal_proyecto`,
  `view_capacidad`, `view_daily`, `view_dashboard`, `view_horas`,
  `view_legacy_tools` y `view_minutas`.

La ruta `/legacy/` sí existe, pero `core.views.portal_home` solo redirige a
Facturabilidad por área, cuenta o detalle de proyecto. No renderiza index ni
fragmentos. Se comprobaron esa implementación, las rutas y las referencias
literales de templates/estáticos en apps/core/config/frontend/tests.

La única prueba que aún leía GSE comprobaba la navegación interna del panel
que ya no se servía. Se retiró ese caso obsoleto y se añadieron cinco pruebas
de las redirecciones vigentes: destino por defecto, proyecto, cuenta, prioridad
de proyecto ante cuenta y exigencia de login. No se retiraron las restantes
pruebas del motor anterior de proyectos: sus comparaciones siguen activas.
Se conservan `core/js/gas_shim.js`, RPC y el motor de portal porque todavía
los usan otras rutas de comparación. No confundirlos con js_main.html retirado.

## Referencias conservadas en pruebas

Antes del borrado se registraron siete snapshots JSON del diseño vigente
desde **1e17d99**: Inversión 1450/900/390 px y Proyecto simple 1450/390 px,
tanto con datos como con datos parciales. Son referencias de cajas, estilos
calculados y, para el proyecto, textos/barras. Las pruebas actuales comparan
contra esos archivos sin necesitar la pantalla anterior. No se actualizan
para hacer pasar una diferencia; su captura inicial ocurrió antes del retiro.

Todas las cuentas mantiene sus pruebas de totales/búsqueda/orden/paginación,
menús, contexto de regreso, error y tres referencias visuales. Se fijó el
reloj del servidor para comparar sus capturas antes/después. Los enlaces
guardados con `vista=anterior` se comprueban explícitamente en las tres rutas.

Después del borrado, las siete referencias estructurales pasan sin cambios,
también con CSP real aplicada solo dentro del navegador de prueba. Las tres
capturas de Todas las cuentas y las cuatro de Proyecto simple son idénticas.
Las tres de Inversión solo difieren en dígitos de la hora de corte de la barra
global; sus cajas/estilos coinciden con los snapshots. No se afirma que las
diez capturas completas sean todas idénticas.

Artefactos locales ignorados: `tmp/fase11/batch-before/`,
`tmp/migration/{investment,project}/` y `tmp/design/all-accounts-reference/`.
Los snapshots JSON sí se versionan en `tests/e2e/snapshots/` para mantener
una verificación repetible del diseño cuando desaparece la comparación.
La inspección de Proyecto simple a 390 px muestra el desborde horizontal que
ya tenía la referencia (captura de 724 px). Se conserva durante esta limpieza;
no confundir igualdad del diseño con una corrección de su adaptación móvil.

## Verificación final

- **1711 pruebas servidor aprobadas**: `pytest tests/portal tests/core
  tests/access tests/capacidad/test_history_range.py tests/test_api.py -q
  --no-cov --tb=short` (103 s). Incluye login/permisos, APIs, redirecciones y
  las cinco nuevas pruebas. La disminución de casos de navegación generados
  desde plantillas retiradas es esperada; no son omisiones ni skips.
- **504 Node aprobadas**: `node --test tests/frontend/*.test.*`. Antes eran
  505; se retiró el caso de navegación del panel GSE no servido, sustituido
  por las cinco pruebas de redirecciones Django. El resto permanece.
- **28 Chrome aprobadas**: `test_inversion.py`, `test_proyecto_simple.py`,
  `test_todas_cuentas.py`, `test_project_independence.py`; con `--no-cov
  --browser-channel chrome --tb=short`. Incluyen las referencias con CSP y
  las cinco familias de proyecto sin descargas del script/shim/RPC antiguo.
- Corridas previas de apoyo (solapadas): 22 Chrome de las tres pantallas,
  33 servidor dirigidas para aliases/API/proyecto y 1688 servidor antes del
  retiro del árbol legacy. No sumar esas corridas como pruebas distintas.
- Ruff/formato (712 archivos), mypy de pages.py y diff de espacios pasan.
  Advertencia existente: `staticfiles/` aún no existe en el entorno de pruebas.

No se toca base de datos, proveedores reales, cálculos, logos compartidos,
Previas al cierre, Horas por mes ni Capacidad diaria. No se activa CSP global
ni ACCESS_ENFORCED y no se hace push en este bloque.

## Lo que sigue

Quedan 25 HTML y 35 estáticos en portal. No todos son huérfanos: las demás
comparaciones y varias pruebas de referencia aún los necesitan. Seguir por
grupos de consumidores y retirar sus alternativas al mismo tiempo que se
conservan las comprobaciones del producto vigente. Bases, servicios JSON,
correo, RPC y CSS compartido no deben borrarse en bloque.

Falta validar CSP completa en las demás ventanas/gráficas/capturas y ejecutar
el cierre general de la fase. Este lote acelera la limpieza, no cierra fase 11.
