# Auditoría independiente de fase 11

27/10/2026. Rama local `main`, HEAD `a370589`. Alcance: cambios de Claude
desde `ee6e31a`, incluyendo retiros de Costos, Oportunidades, Cuenta,
Business Overview, traslado del detalle a referencia de pruebas, CSP,
retiro del RPC público y limpieza de maquetas. Sin modificar código
versionado, credenciales, datos, temporales ajenos o accesos. Sin push.

## Resultado

No se detectó regresión funcional por los retiros en las suites ejecutadas.
La aplicación no referencia los assets de `portal/` retirados; sus directorios
ya no están en apps/portal. Los servicios actuales no se eliminaron. El
frontend no cambió en este conjunto de commits: se retiraron presentaciones
anteriores y se ajustaron entradas del servidor, pruebas y configuración.

El detalle anterior y su shim están en tests/reference, fuera de los
directorios estáticos/plantillas normales. Config/urls no monta RPC ni
tests/reference; la prueba de rutas reales comprueba 404 del RPC. La entrada
de proyecto mantiene permisos, visibilidad del ID y CSRF. Los antiguos
ejecutiva/comercial necesarios para la precarga se conservan y usan frontend.

El commit a370589 elimina 56 archivos de maquetas de design/ y archiva notas
bajo docs/archivo; no modifica apps, core, config, frontend ni tests.

## CSP

Activa por defecto en base/producción, sin unsafe-inline ni unsafe-eval.
Importmap con nonce por petición; estilos de captura admitidos por dos hashes
exactos. Preview de logos admite blob solo como imagen. Admin/static quedan
excluidos deliberadamente. ACCESS_ENFORCED no se activó por defecto.

Se validaron 61 casos Chrome con CSP_ENFORCE=True y config.urls, quitando
los directorios de referencia de las plantillas y estáticos. Incluyen seis
pantallas de humo, las cinco familias de proyecto y sus pestañas, Cuenta,
Costos, Comercial, exportación PNG real y simulada, y carga/borrado de logos.
El adaptador temporal agrega comprobación de errores CSP en todos estos
casos; ninguna violación detectada. Proveedores externos bloqueados por las
fixtures y datos de prueba. No es una certificación de todos los formularios
ni una nueva ejecución de toda la suite e2e.

La prueba de preview que convierte Report-Only en CSP se ejecuta aparte en
su preparación original, porque requiere la cabecera Report-Only. Las dos
pruebas de carga/borrado de logos sí se ejecutaron con la cabecera real de
producción. No se cambia el test versionado.

## Hallazgos pendientes

Actualización documental del 27/10 posterior a la auditoría: los puntos 1 y
2 se corrigieron en AGENTS, plan, traspaso y estado-csp. Los demás siguen
pendientes. La rama local congelar-referencias contiene el piloto 4103ed6,
fuera de main; no se incluyó en las suites independientes descritas aquí.

1. Documentación contradictoria: AGENTS/traspaso aún dicen que el último
   bloque fue Comercial, que quedan 11 HTML/29 estáticos y que CSP está sin
   activar. El plan contiene esos estados y un bloque posterior que todavía
   marca _modern/anterior_disponible como pendientes, aunque ya no existen.
   Actualizar el estado vigente sin reescribir la evidencia histórica.
2. La instrucción «CSP_REPORT_ONLY=1 solo anota» es incompleta. Con
   CSP_ENFORCE=True el middleware prioriza el bloqueo. Para solo reportar
   deben configurarse CSP_ENFORCE=0 y CSP_REPORT_ONLY=1 conjuntamente.
3. tests/conftest.py activa reference_site automáticamente para toda la
   suite: pruebas normales usan rutas diferentes de producción. La auditoría
   temporal separa ambas configuraciones. Conviene mantener una suite
   permanente con config.urls, CSP real y sin directorios de referencia.
4. Congelación pendiente aceptada: 41 archivos Node aún leen el script
   anterior. No borrar tests/reference hasta preservar esos resultados y las
   comparaciones de navegador. La fase 11 no está cerrada.
5. No borrar core/rpc en bloque después de congelar: warm_cache importa
   get_rpc_function (líneas 14 y 334), y numerosos módulos registran funciones
   internas. Primero separar transporte HTTP/política antiguos del registro
   y servicios aún utilizados. No es una avería actual; es un riesgo del plan
   de limpieza de docs/retiro-detalle-anterior.md.

## Comprobaciones

- 1759 servidor aprobadas, sin omisiones (97 s): tests/portal tests/core
  tests/access tests/capacidad/test_history_range.py tests/test_api.py,
  --no-cov --tb=short.
- 472 Node aprobadas, sin omisiones: node --test tests/frontend/*.test.*.
- 61 Chrome aprobadas con rutas reales y CSP, un caso seleccionado aparte
  por su preparación Report-Only. Registro audit-phase11-production-csp.log.
  Ese caso de preview también pasó en su ejecución separada: 1 aprobada
  (3 s), registro audit-phase11-logo-report-mode.log.
- Ruff aprobado para apps/core/config/tests excluyendo test_zz_*.py ajenos;
  mypy de pages.py aprobado; manage.py check sin incidencias y collectstatic
  --dry-run --noinput terminado. No se hizo collectstatic real de producción.
- Primera ejecución del adaptador temporal falló antes de los tests porque
  STATICFILES_DIRS contiene tuplas de prefijo/ruta; corregido solo en tmp y
  repetido. No fue un fallo del código de main.

Registros y adaptador en tmp/audit-phase11-*.log y tmp/audit_phase11_plugin.py.
Los cambios ajenos de tools/migracion y test_zz/shots_tmp permanecen intactos.
