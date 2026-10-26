# Fase 11: EVA 2 y Capacidad mensual

Base anterior al retiro: **7420d17**. El usuario pidió continuar sin asumir
riesgos por acelerar. Se limitó el bloque a dos plantillas y sus consumidores.

## Cambios

- Retiradas `apps/portal/templates/portal/eva2.html` y
  `apps/portal/templates/portal/capacidad_instalada.html`.
- Las rutas de EVA 2 y Capacidad mensual usan `_current`, manteniendo
  constructor de contexto, permisos y login de las vistas originales. Sus
  respaldos de render apuntan a las mismas plantillas de frontend. No se
  elimina lógica de vistas ni servicios, ni se modifica el CSV de Capacidad.
- `vista=anterior` abre las páginas vigentes y conserva los filtros. No
  permite evadir permisos: seis casos nuevos cubren capacidad incorrecta,
  alcance limitado y login anónimo en ambas rutas.
- No se modifica Capacidad diaria, su origen Histórico/Azure, ni las fórmulas,
  datos de EVA 2, logos compartidos o importes de Comercial.

## Referencias y cobertura

Antes de retirar las plantillas se registraron **seis snapshots del diseño
vigente**, a 1450/900/390 px en ambas pantallas. Se versionan como
`tests/e2e/snapshots/{capacity,eva2}_layout_<ancho>.json`. Comparan cajas,
estilos calculados y, en EVA 2, el contenido completo de las tablas.

Las pruebas de comparación antigua se sustituyeron por estas referencias:
no se reemplazaron por comparar dos veces la pantalla actual. La prueba de
EVA 2 solo estaba parametrizada para screen=2; se retiraron las ramas muertas
de históricos de EVA 1/3 de esa función, conservando sus pruebas separadas.

Después del retiro, las referencias también se ejecutan con CSP real aplicada
solo en el navegador de prueba. Las capturas completas antes/después tienen
los mismos tamaños y solo cambian los dígitos de la hora global. No se afirma
igualdad píxel a píxel de esas capturas completas.

Se conserva el desborde móvil previo: Capacidad mensual genera una captura de
926 px con viewport de 390 px y EVA 2 de 431 px. Corregirlo sería un cambio de
diseño independiente; este bloque conserva la referencia solicitada.

Nuevos casos de navegador verifican que los enlaces guardados a las versiones
anteriores conservan filtros, CSV filtrado y regreso. La primera corrida tuvo
un fallo en el caso nuevo de EVA 2: comprobaba IDs de proyecto en la primera
tabla (resumen por DM), en vez de la tabla de proyectos. Se corrigió el selector
de la prueba, sin tocar la pantalla ni omitir el caso, y se repiten los dos
archivos completos.

Artefactos locales ignorados: `tmp/fase11/capacity-eva2-before/` y
`tmp/migration/{capacity,eva2}/`; logs `tmp/phase11-capacity-eva2-*.log`.

## Verificación

- **1715 servidor aprobadas**: `pytest tests/portal tests/core tests/access
  tests/capacidad/test_history_range.py tests/test_api.py -q --no-cov
  --tb=short` (94 s), sin fallos ni omisiones. El contexto del CSV de
  Capacidad y sus filtros, los resúmenes/errores de EVA 2 y los permisos
  existentes siguen comprobándose.
- **504 Node aprobadas**: `node --test tests/frontend/*.test.*`.
- **34 Chrome aprobadas**: `pytest tests/e2e/test_capacidad.py
  tests/e2e/test_eva123.py -q --no-cov --browser-channel chrome --tb=short`
  (45 s). Incluyen CSV/filtros/regreso, las seis referencias con CSP real y
  los flujos vigentes/históricos de EVA 1–3. Primera corrida: 33 aprobadas y
  el selector incorrecto de la prueba nueva; repetición completa aprobada,
  sin omitir ni marcar fallos como esperados. No sumar casos solapados.
- Ruff y formato de apps/core/tests (712 archivos), mypy de pages.py y
  comprobación de espacios aprobados. Advertencia existente: staticfiles/
  no está creado en el entorno de pruebas.

## Continuación

Quedan **23 HTML y 35 estáticos** en portal. El resto de comparaciones, sus
bases compartidas y el motor antiguo conservan consumidores: no retirarlos
de golpe. Fase 11 sigue abierta por esas referencias y la validación CSP
integral. No se activa CSP global ni ACCESS_ENFORCED; sin push de este bloque.
