# Entrada a fase 11 (26/10/2026)

La fase 10 sigue cerrada. El usuario autorizó integrar los cambios nuevos y
preparar la fase 11. Este bloque valida la integración; no elimina todavía
referencias ni activa una política de bloqueo global.

## Integración revisada

- Base revisada: `24cd3cf` (diseño/logos) y `834bbfa` (fechas de Capacidad).
  Se conserva el diseño nuevo solicitado; no se exige volver al diseño previo
  a esos commits. Las comparaciones históricas siguen disponibles.
- Aplicada localmente `portal.0003_account_logo`, con respaldo consistente
  previo de SQLite en `tmp/backups/before-account-logo-20261026-123443.sqlite3`.
  La copia y la base están ignoradas por Git. En otros entornos se debe ejecutar
  `python manage.py migrate` antes de usar los logos; el commit no distribuye
  una base ya migrada.
- Tipado de `service_distribution` corregido y tres archivos formateados.
- Restaurado el contrato anterior de rangos MPB repetidos: `resolve()` y
  `resolve_full()` abarcan todas las filas del mismo ID. El commit `48068c0`
  ya usaba ese rango; la integración lo había limitado a la primera fila
  salvo petición explícita de rango completo. Eso afectaba consumidores como
  Proyecto simple y la precarga. La prueba comprueba ambos órdenes de filas.
  No se alteran filtros explícitos de fechas ni fórmulas de horas/costos.
- Se conservan los cambios funcionales del compañero: booking por periodo,
  porcentajes vendidos fraccionarios, meses futuros pendientes y fechas de
  Capacidad desde Histórico con respaldo Azure. No son cambios solo visuales;
  no se revierten durante la limpieza.
- CSP permite `blob:` únicamente en imágenes para las vistas previas locales.
  La prueba de navegador aplica la cabecera de bloqueo a la página de Cuenta
  solo durante ese caso y comprueba que la imagen se decodifica (80 px).
  La configuración normal continúa sin bloqueo y sin activar ACCESS_ENFORCED.

## Evidencia de este bloque

- 388 pruebas de servidor aprobadas: `tests/clockify`, `tests/ejecutivo`,
  `tests/capacidad/test_history_range.py`, y archivos de `tests/portal/`:
  `test_account_hours.py`, `test_account_logos.py`, `test_project_detail_api.py`,
  `test_operativa_api.py`, `test_margins_api.py`, `test_roster.py`,
  `test_facturability.py`; también `tests/core/test_frontend_support.py`.
- 498 Node aprobadas: `node --test tests/frontend/*.test.*`.
- 74 pruebas Chrome aprobadas en `tests/e2e/test_operativa.py`,
  `test_account_logos.py`, `test_project_independence.py`, `test_page_capture.py`
  y `test_facturabilidad.py`.
- Después del ajuste CSP: 15 aprobadas al repetir `tests/e2e/test_account_logos.py`
  completo (4 casos, uno nuevo) y `tests/core/test_frontend_support.py` (11).
  Estos casos se solapan con los anteriores; no sumar como pruebas distintas.
  La primera prueba nueva falló por usar un método incorrecto del objeto
  APIResponse de Playwright; se corrigió a `response.headers` y se repitió
  todo el archivo sin omisiones ni fallos.
- Ruff y formato: aprobados sobre `apps core tests`, excluyendo únicamente
  los diagnósticos ajenos `test_zz_*.py`; 706 archivos formateados correctamente.
  Mypy de `apps/portal/pages.py`, Django check y detección de migraciones:
  aprobados. La advertencia de `staticfiles/` ausente en pruebas sigue presente.
- Editor de logo móvil inspeccionado en
  `tmp/design/logo-upload-reference/editor-390.png`; las pruebas también
  revisan escritorio, persistencia, eliminación y ausencia de desborde móvil.
  No es una nueva validación visual integral de todo el rediseño.

## Orden de trabajo restante

1. **Separar referencias y producto activo.** La búsqueda en plantillas de
   `frontend/` no encuentra referencias a `portal/js`, `portal/css` o `legacy/`.
   El grafo de Proyecto y sus pruebas de red siguen sin script/shim/RPC.
   Aun así hay 33 HTML y 37 archivos estáticos en los directorios anteriores.
   Son inventario, no autorización de borrado masivo: identificar consumidores
   indirectos, plantillas base, pruebas de tokens y referencias visuales.
2. **Retirar rutas de comparación y sus pruebas de forma coordinada.**
   `pages.py` todavía tiene `anterior_disponible()` y `_modern()`; Costos usa
   `anterior=1` y `vista=proyectos` tiene otro significado. Unos 103 archivos de
   pruebas mencionan una ruta/referencia anterior o archivos estáticos anteriores.
   No borrar archivos de prueba completos si también cubren la ruta vigente.
   Mantener sus casos funcionales y sustituir las comparaciones por referencias
   visuales del diseño aprobado antes de retirar los originales.
3. **Conservar los servicios del backend.** Las rutas de actualización,
   acuerdos, ingresos, costos y cuenta financiera en `views.py` devuelven JSON;
   no son pantallas antiguas que puedan borrarse por su ubicación. Varias
   páginas nuevas también reutilizan contexto Python mediante `render_page()`.
   No borrar `views.py`, cálculos, APIs ni CSV en bloque.
4. **Validar CSP completa antes del bloqueo.** El importmap tiene nonce y las
   plantillas nuevas no contienen eventos/estilos HTML en línea. El caso del
   logo queda probado, pero no certifica todas las pantallas. Revisar captura
   global (`ui/page-capture.js` y html2canvas generan estilos en un documento
   clonado), gráficos, ventanas, descargas, fuentes y logos bajo política real.
   Asignar propiedades CSS con `node.style` no prueba por sí solo una infracción;
   medir violaciones en navegador antes de cambiar el diseño o la política.
5. **Cierre.** Repetir suite general, comparaciones visuales del diseño vigente,
   permisos limitados, filtros/CSV/regreso de Horas por mes y red del detalle.
   Documentar evidencia antes de marcar fase 11 terminada. No activar accesos
   Genesis, enviar correo real ni hacer push sin petición expresa.

Los temporales de migración y los cuatro `tests/e2e/test_zz_*.py` siguen ajenos,
sin modificar ni incluir en commits. Añadir archivos siempre por nombre.
