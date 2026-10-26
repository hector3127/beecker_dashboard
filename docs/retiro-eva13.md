# Fase 11: retiro de las plantillas anteriores de EVA 1 y EVA 3

Base: **8c47a2c**, 26/10/2026. Retiradas las cinco plantillas de portal:
`eva1.html`, `eva3.html`, `_eva_table.html`, `_eva_closed.html` y
`_eva3_closed.html`. Sus únicos consumidores eran las páginas anteriores,
los respaldos de las vistas Python y las pruebas del script inline.

Las entradas activas y el respaldo Python sirven las plantillas/fragmentos de
frontend. Los enlaces guardados con `vista=anterior` siguen funcionando con
la pantalla vigente. Se conservan las rutas de históricos HTML y API, las
cargas diferidas, CSV, logos compartidos y cambios de diseño de Christian.
No se modifican modelos vigentes, servicios, fuentes, fórmulas ni cifras.
EVA 3 conserva la cookie CSRF. No se retira ningún shim o servicio compartido.

Los fragmentos delegan el acceso en sus vistas originales: cuando se exige
login, EVA 1 conserva 401 y EVA 3 redirige al acceso. No se introduce el
redireccionamiento común de `_current` para esos fragmentos.

## Referencias previas al retiro

- Doce snapshots de diseño vigente: EVA 1 y EVA 3, tabla activa e histórico
  abierto, a 1450/900/390 px. Se registraron antes de borrar y después se
  comprueban con CSP aplicada en el navegador. Incluyen cajas, estilos y texto
  completo de tablas. Los snapshots no se regeneran después del retiro.
  Las doce capturas conservan dimensiones y contenido: once solo difieren en
  el minuto de actualización global. El histórico EVA 3 a 1450 px también
  varía levemente en gradientes/sombras (máximo 9/255 en un canal), sin cambios
  de cajas/estilos/textos; diferencia amplificada y pantalla inspeccionadas.
  Se conserva el desborde móvil preexistente de EVA 1 (PNG de 435 px para
  viewport de 390 px); no se rediseña durante la limpieza.
- El código inline anterior se ejecutó antes de eliminarlo y se verificó
  contra el actual. Sus salidas se guardan en
  `tests/frontend/snapshots/eva_models.json`: cuatro combinaciones de filtros
  con visibilidad y CSV completo, cuatro conversiones de fecha y tres casos
  del promedio de costo (vacío, pendiente y mezcla con presupuesto cero).
  Las dos pruebas Node conservan todos esos casos mediante esas salidas,
  sin ejecutar el código retirado ni usar el modelo actual para generarlas.

La primera captura del histórico de EVA 3 falló en tres tamaños porque la
prueba nueva esperaba `eva3-closed-table`; la tabla vigente se llama
`eva3-history-table`. Se corrigió el selector de la prueba y se capturaron los
doce casos antes del retiro, sin cambiar producción.

## Cobertura

Se conservan todas las pruebas existentes de EVA 1–3, incluidas las aportadas
para diseño de logos, menús de columnas, históricos, paginación, exportación
filtrada, errores y reintentos. Los recorridos de filtros/CSV/histórico de EVA
1 y consumo/histórico/regreso de EVA 3 se repiten con el enlace obsoleto.

Doce pruebas de servidor nuevas verifican página/fragmento vigente con y sin
ese parámetro, error de fuente y respuesta original de login sin leer datos.
Otros doce casos de permisos extienden a las cuatro rutas el rechazo por
capacidad incorrecta, alcance limitado y acceso anónimo.

## Verificación del bloque

- `node --test tests/frontend/*.test.*`: **502 aprobadas**, sin omisiones.
- `pytest tests/e2e/test_eva123.py -q --no-cov --browser-channel chrome
  --tb=short`: **43 aprobadas**, sin omisiones (54 s), incluidas las doce
  referencias con CSP y los flujos con enlaces obsoletos.
- `pytest tests/portal tests/core tests/access
  tests/capacidad/test_history_range.py tests/test_api.py -q --no-cov
  --tb=short`: **1751 aprobadas**, sin omisiones (109 s), incluidas las nuevas
  comprobaciones de plantilla, fragmentos, permisos y respuestas de login.
- Ruff pasa excluyendo los `test_zz_*.py` ajenos (sus dos E501 previos no se
  tocan). Mypy de pages.py aprobado. No se activan accesos ni CSP globales.

Capturas y registros locales ignorados en `tmp/fase11/eva13-before/`,
`tmp/migration/eva13/`, `tmp/phase11-eva13-*.log`. Capturador del código
anterior en `tmp/capture-eva.mjs`, ajeno al producto y a las pruebas versionadas.

## Pendiente

Quedan **13 HTML y 30 estáticos** de portal. Otras comparaciones y sus
dependencias compartidas aún se usan; continuar su retiro por bloques y
completar la certificación integral CSP. Fase 11 sigue abierta. No se hace
push en este bloque; temporales ajenos intactos.
