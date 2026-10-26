# Fase 11: retiro de la presentación anterior de Delivery Manager

Base: **f38602b**, 26/10/2026. Se retiran la plantilla
`portal/delivery_manager.html` y su vista HTML `views.delivery_manager`.
La ruta mantiene la entrada modular `pages.delivery_manager`, incluso con
`vista=anterior` o `bloque=inv` guardados. La página no consulta fuentes;
la API conserva su carga por pasos y el frontend decide cómo presentar
errores, inexistencia del DM y regreso a Operativa.

No se cambian cálculos, datos, alcance por cuenta, caché ni servicios.
`dm_state`, `dm_rows`, `ManagerUnavailableError` y sus auxiliares siguen
utilizados por la API y el precalentamiento: no se retiran. Tampoco se
modifican los módulos vigentes, los logos compartidos ni la presentación.

## Evidencia previa al retiro

Seis referencias del diseño vigente se guardaron antes de borrar: página y
detalle de horas mensual abierto, a 1450/900/390 px. Snapshots de cajas,
estilos y texto completo de tablas en `tests/e2e/snapshots/dm_layout_*`.
Después del retiro se repiten con CSP realmente aplicada en el navegador;
los snapshots no se regeneran desde la nueva ejecución.
Las seis capturas mantienen dimensiones y contenido: cinco solo difieren
en el minuto de actualización global. El detalle móvil tiene además variación
de composición de color de hasta 2/255 por canal, sin cambios geométricos,
de estilos ni texto. Captura completa y diferencia amplificada inspeccionadas.

Las seis pruebas servidor que usaban la plantilla anterior mantienen sus
comprobaciones de datos mediante la API y el servicio original: nombre,
proyectos, demora, presupuesto excedido, inexistencia, error de fuente,
clave de cuenta, ID de proyecto y promedio T/C. El enlace real a proyecto y
su navegación de regreso se conservan en navegador, con y sin parámetro
obsoleto. El 502 de la API sigue provocando regreso a Operativa en la UI;
no se impone al endpoint la redirección de la vista HTML retirada.

Seis pruebas servidor adicionales comprueban plantilla actual, nombre/slug,
montaje sin leer fuentes, login y capacidad incorrecta, con y sin el enlace
obsoleto. Los casos de alcance limitado, caché por alcance y datos pendientes
ya existentes en `test_manager_api.py` se conservan.

## Verificación

- Dirigida inicial: **69 aprobadas** (`test_views.py`, `test_manager_api.py`,
  `test_manager_precache.py`), antes de añadir los seis casos de página.
- `node --test tests/frontend/*.test.*`: **502 aprobadas**, sin omisiones.
- `pytest tests/e2e/test_delivery_manager.py -q --no-cov
  --browser-channel chrome --tb=short`: **22 aprobadas**, sin omisiones
  (30 s), incluidas las seis referencias con CSP de prueba.
  Tras reforzar las comprobaciones de href a cuenta y de ruta de proyecto,
  se repitieron sus dos casos con `-k links_carry`: ambos pasan (8 s).
- `pytest tests/portal tests/core tests/access
  tests/capacidad/test_history_range.py tests/test_api.py -q --no-cov
  --tb=short`: **1756 aprobadas**, sin omisiones (108 s), incluidas las
  seis pruebas nuevas de página sin fuentes, login y capacidad.
- Ruff sin temporales ajenos, formato (671 archivos), mypy de pages.py y
  espacios aprobados. Los dos E501 ajenos ya documentados no se modifican.

Artefactos locales ignorados: `tmp/fase11/dm-before/`,
`tmp/migration/delivery_manager/` y `tmp/phase11-dm-*.log`.

## Pendiente

Quedan **12 HTML y 30 estáticos** de portal. Continuar con otras comparaciones
y componentes todavía usados; después completar la certificación CSP
integral. No activar accesos ni CSP global, ni retirar el shim compartido.
Fase 11 sigue abierta; sin push. Temporales ajenos intactos.
