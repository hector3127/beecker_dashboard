# Fase 11: retiro de la presentación anterior de Facturabilidad por área

Base de comparación: **3a8ae34** (26/10/2026). Se retiran únicamente
`portal/facturabilidad_area.html`, `portal/css/facturabilidad_area.css` y
`portal/js/facturabilidad_area.js`. La entrada usa `_current`; el respaldo de
la vista Python apunta a `pages/billability_area.html`.

No se modifican modelos vigentes, servicios GSE, fuentes, fórmulas, datos,
permisos ni diseño. Se conserva el contexto del año y la cookie CSRF de la
vista. El enlace obsoleto `vista=anterior` ahora sirve la pantalla modular.
`/legacy/` conserva sus redirecciones generales y por proyecto. El shim sigue
presente para otras comparaciones; no se borra en este bloque.

## Referencias registradas antes del retiro

- El script anterior se ejecutó ANTES de borrarlo: dos publicaciones de lotes,
  doce combinaciones de área/jornada/mes, 144 agregados mensuales y sus días
  laborables, doce resultados de recursos/bajas y trece resultados KPI (uno
  con persona seleccionada). Salidas completas guardadas en
  `tests/frontend/snapshots/billability_area_model.json`; las dos pruebas del
  modelo actual las comparan sin ejecutar el archivo retirado ni regenerarlas
  desde la implementación que se está probando.
- Dieciocho referencias del diseño vigente se capturaron antes de borrar:
  General, Detalle recurso, KPIs, % Recurso, Detalle HRS y área DEV, cada una a
  1450/900/390 px. Los snapshots comprueban cajas, estilos y tablas. Todos se
  repitieron después con CSP realmente aplicada en el navegador y sin errores.
- Diecisiete capturas completas vigentes son idénticas píxel a píxel. General
  a 900 px conserva dimensiones, cajas, estilos y texto exactos; solo varían
  componentes de color hasta 2/255 en zonas de sombra/gradiente. Se inspeccionó
  la diferencia amplificada y la captura completa; no hay cambio geométrico.

La navegación de apartados se selecciona en escritorio antes de medir móvil,
igual que en las pruebas anteriores: su ocultación móvil preexistente no se
rediseña durante esta limpieza.

## Cobertura conservada

Se retiran dos pruebas Node que ejecutaban el controlador RPC eliminado.
Su comportamiento está cubierto en navegador actual: carga inicial solo de
metadatos (ahora prueba explícita con año 2025), error de fuente sin solicitar
horas y reintento (caso ya existente). No se elimina ni omite la comparación
de cálculos. El recorrido de los cinco apartados, filtros y CSV se ejecuta
con y sin `vista=anterior`. Tres casos nuevos comprueban que ese parámetro no
evita alcance limitado, capacidad incorrecta o login.

## Verificación

- **54 Chrome aprobadas**: `pytest tests/e2e/test_facturabilidad_area.py
  tests/e2e/test_facturabilidad.py -q --no-cov --browser-channel chrome
  --tb=short` (81 s). Incluyen referencias, filtros, festivos, CSV, carga
  parcial/deduplicación, caché, IDs, actualización forzada, error/reintento y
  regreso a Operativa. Sin omisiones ni conexiones a proveedores reales.
- **502 Node aprobadas**, sin omisiones: `node --test tests/frontend/*.test.*`.
  El descenso de 504 a 502 corresponde a los dos tests del controlador RPC
  retirado y cubierto en navegador, no a pruebas de cálculos eliminadas.
- **1729 servidor aprobadas**, sin omisiones: `pytest tests/portal tests/core tests/access
  tests/capacidad/test_history_range.py tests/test_api.py -q --no-cov
  --tb=short` (111 s). Incluye rechazo de acceso con el parámetro obsoleto,
  cookie CSRF, año elegido, API y redirecciones de /legacy/.
- Ruff pasa con `--exclude 'test_zz_*.py'`; la revisión completa solo señala
  E501 preexistentes en los temporales ajenos `test_zz_seq.py` y
  `test_zz_styles.py`, sin modificarlos. Formato de apps/tests (670 archivos),
  mypy de pages.py y comprobación de espacios aprobados.

Artefactos ignorados: `tmp/fase11/area-before/`,
`tmp/migration/billability_area/`, `tmp/fase11/area-diff.png`, capturador
`tmp/capture-area-model.mjs` y registros `tmp/phase11-area-*.log`.
Los snapshots versionados no se actualizaron después de retirar los archivos.

## Pendiente

Quedan **18 HTML y 30 estáticos** en los directorios anteriores de portal.
Continuar con las demás comparaciones y dependencias aún usadas, y después
certificar CSP integral. No activar CSP global ni ACCESS_ENFORCED, ni retirar
servicios/shim todavía utilizados. Fase 11 abierta; sin push de este bloque.
