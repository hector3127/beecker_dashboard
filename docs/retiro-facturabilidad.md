# Fase 11: Facturabilidad general, especialidad y recurso

Referencia de partida: **18e69a1**. Este bloque retira solo las tres
alternativas antiguas y conserva las pantallas vigentes, sus cálculos y
componentes compartidos.

## Archivos y rutas

Se eliminan las plantillas `portal/facturabilidad.html`,
`portal/facturabilidad_especialidad.html` y `portal/facturabilidad_recurso.html`.
Las tres rutas usan `_current` y sus vistas Python tienen el mismo respaldo
de render en frontend. No se borran sus servicios ni se modifican horas,
porcentajes, rangos, roles o estados de baja.

Facturabilidad por área se mantiene sin cambios, con su comparación anterior
todavía disponible. No se retiran `_period_picker.html`, CSS compartido, APIs,
motor de proyectos ni shim: otras referencias los usan.

Los enlaces guardados con `vista=anterior` abren la pantalla vigente conservando
mes y roles. Las pruebas de servidor comprueban ambos tipos de enlace: las
plantillas actuales y sus assets, login, capacidad y alcance limitado, y que
las fuentes no se consultan cuando se rechaza el acceso.

## Referencias de diseño y datos

Se registraron **nueve snapshots ANTES de retirar las plantillas**, con datos
de prueba idénticos: las tres pantallas a 1450/900/390 px. Incluyen cajas,
estilos calculados y texto completo de las tablas. Archivos versionados:
`tests/e2e/snapshots/billability_layout_<pantalla>_<ancho>.json`.

La prueba antigua de Recurso comparaba datos entre dos páginas. Se reemplaza
por estas referencias vigentes, no por comparar dos veces el mismo renderer.
Las pruebas funcionales existentes siguen cubriendo cambio entre mes/trimestre/
año, roles, pestañas y regreso, colores de datos ausentes, modo de gráfica
horas/porcentaje, selección, ampliación, filtros de columna y errores de fuente.

Después del retiro, las nueve referencias se ejecutan con CSP de bloqueo solo
en el navegador de prueba. Las capturas antes/después conservan estructura y
tamaños; seis son idénticas, y las tres de escritorio solo difieren en los
dígitos de la hora global. No se actualizaron snapshots para ocultar diferencias.

Artefactos locales ignorados: `tmp/fase11/billability-before/` y
`tmp/design/billability-retirement/`. Logs en `tmp/phase11-billability-*.log`.

La primera corrida de navegador dio 33 aprobadas y tres fallos en los casos
nuevos de enlaces guardados: la prueba esperaba que el summary del selector
dijera QA, pero el título vigente es «Áreas mostradas». Se corrigió la prueba
para verificar el estado real de las casillas QA/DEV y los datos filtrados,
sin modificar producción ni desactivar los casos. Se repiten ambos archivos
completos antes de cerrar el bloque.

## Estado posterior

Validación de servidor: **1724 aprobadas**, sin fallos ni omisiones, con
`pytest tests/portal tests/core tests/access tests/capacidad/test_history_range.py
tests/test_api.py -q --no-cov --tb=short` (99 s). Incluye doce comprobaciones
adicionales de plantillas/accesos con el parámetro antiguo y conserva las
pruebas de fórmulas, periodos y carga de fuentes existentes.

**504 Node aprobadas** con `node --test tests/frontend/*.test.*`.
**36 Chrome aprobadas** con `pytest tests/e2e/test_facturabilidad.py
tests/e2e/test_kpis_dm.py -q --no-cov --browser-channel chrome --tb=short`
(50 s). Se repitieron ambos archivos completos después de corregir la
expectativa de los tres casos nuevos, sin omisiones ni fallos esperados. La
primera corrida (33 aprobadas, tres fallos de prueba) no se suma como casos
adicionales a esta revalidación.
Ruff/formato (712 archivos), mypy de pages.py y diff de espacios aprobados.
Se conserva la advertencia previa de `staticfiles/` no creado en pruebas.

Quedan **20 HTML y 35 estáticos** en portal. Fase 11 sigue en curso: otras
comparaciones y certificación CSP integral pendientes. No se activa CSP global
ni ACCESS_ENFORCED; no se modifican logos, Comercial, Capacidad diaria ni
Horas por mes. Los temporales ajenos se conservan. Sin push de este bloque.
