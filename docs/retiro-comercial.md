# Fase 11: retiro de la presentación anterior de Comercial

Base: **ddb8ec2**, 26/10/2026. Retiradas `portal/comercial.html` y
`portal/css/commercial_layout.css`. La ruta activa siempre sirve
`pages/commercial.html`, también con el parámetro obsoleto `vista=anterior`.
`views.comercial` se conserva porque `warm_cache` la utiliza; ahora entrega
la misma plantilla vigente. No borrar ese punto de entrada ni
`comercial_response` o sus servicios de caché/contexto.

No se modifican modelos, fórmulas, fuentes, permisos, datos ni diseño. Se
conserva el importe de oportunidades abiertas de «Previas al cierre» corregido
en 47d0364. Los filtros y la navegación mantienen origen, rango de fechas y
año de referencia. No se modifica JavaScript/CSS de la pantalla actual.

## Referencias antes del retiro

Seis snapshots de diseño vigente guardados antes de borrar: entrada directa
y desde Business Overview a 1450/900/390 px, con el desglose por servicio
abierto. Registran cajas, estilos y texto de indicadores/secciones/tablas.
Después del retiro pasan con CSP aplicada de verdad en el navegador. Las
seis capturas conservan dimensiones y contenido; solo varía el minuto en la
barra superior. Captura completa inspeccionada; snapshots no regenerados
después del retiro.

## Cobertura conservada

Las pruebas de navegación y compilación apuntan a la plantilla vigente.
Los casos de caché siguen comprobando reutilización de contexto, filtros
independientes, corte guardado ante fallo y error de fuente sin almacenar.
Los indicadores `data-portal-ready` y `cached_page.js` pertenecían a la base
anterior y ya estaban ausentes de la pantalla modular antes de este bloque;
sus comprobaciones se sustituyen por las del contexto pasado a render y el
mensaje real de error. No se reintroducen esos hooks ni se modifica el
comportamiento actual del refresco.

La primera suite dirigida pasó 40 casos, pero después de terminar una prueba
disparó la actualización ejecutiva de fondo e intentó resolver Google y
Clockify, con errores de DNS y de logging al cerrarse la captura. Se aisló
`request_refresh` en las pruebas de navegación y en el caso de precarga
ejecutiva que no debe leer fuentes. Solo se modifica el aislamiento de las
pruebas; no se cambia la actualización de producción.

Se añaden seis casos de rechazo de alcance limitado/capacidad incorrecta/
anónimo, con y sin el parámetro obsoleto, antes de leer contexto. En navegador
el desglose/cambio de año se prueba con ambos enlaces, y dos casos nuevos
comprueban el regreso a Business Overview con las mismas fechas después
de cambiar el año de referencia.

## Verificación

- **11 Chrome aprobadas**, sin omisiones (15 s): `pytest
  tests/e2e/test_comercial.py -q --no-cov --browser-channel chrome --tb=short`.
  Incluye seis referencias con CSP, cambio de año y regreso con fechas.
- **502 Node aprobadas**, sin omisiones: `node --test tests/frontend/*.test.*`.
- `pytest tests/portal tests/core tests/access
  tests/capacidad/test_history_range.py tests/test_api.py -q --no-cov
  --tb=short`: **1761 aprobadas**, sin omisiones (101 s), después de aislar
  la actualización de fondo en las pruebas de navegación/precarga.
- Ruff excluyendo los temporales ajenos, formato (671 archivos), mypy de
  pages.py y espacios aprobados. Los E501 ajenos ya documentados no se tocan.

Artefactos ignorados en `tmp/fase11/commercial-before/`,
`tmp/migration/commercial/` y `tmp/phase11-commercial-*.log`.

## Pendiente

Quedan **11 HTML y 29 estáticos** de portal, con otras comparaciones y
dependencias compartidas aún usadas. Continuar por bloques y completar la
certificación integral de CSP. No activar política ni accesos globales;
temporales ajenos intactos. Fase 11 abierta; sin push.
