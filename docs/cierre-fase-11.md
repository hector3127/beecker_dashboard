# Cierre de la fase 11 (30/10/2026)

Instrucción del usuario: el diseño nuevo (dashboards de proyecto y el resto de
la interfaz) **es la línea base aprobada**. «Conservar el diseño del old» ya no
aplica. Los documentos anteriores que lo piden (reglas de igualdad visual,
«comparar contra ?vista=anterior», «congelar contra el original») están
desfasados; si contradicen esta página, manda esta página.

## Principio

Cerrar la fase 11 es **dejar de mirar atrás**, no congelar el pasado:

- No se congelan las comparaciones contra el detalle de proyecto anterior: se
  borran. Un JSON con la foto del diseño actual no protege nada y hay que
  regenerarlo cada vez que se ajusta el diseño.
- Se **conservan** las pruebas de funcionamiento (guardar, error con reintento,
  permisos, alcance, respuestas tardías, texto seguro) y los JSON de Node de
  `tests/frontend/frozen/`, que validan **cálculos** (regla de negocio), no
  apariencia.
- El diseño nuevo se protege con una prueba de humo corta (ver paso 2), no con
  capturas byte a byte.
- No cambiar cálculos ni reglas de negocio. Sigue vigente: no activar
  `ACCESS_ENFORCED`, no tocar Horas por mes, CSP obligatoria.

## Pasos

1. **Borrar las comparaciones con el original.** Hecho el 30/10: 53 funciones
   (`*_match_previous`, `test_unchanged_shared_view`, `test_entry_matches_previous`,
   etc.) en 41 archivos de `tests/e2e`. Los archivos conservan sus pruebas
   funcionales y sus ayudantes.
2. **Prueba de humo del diseño nuevo.** Hecho el 30/10:
   `tests/e2e/test_project_design_sections.py::test_populated_section_at_each_size`
   (18 pestañas AER/IXB × 5 anchos, con la CSP aplicada) comprueba que no hay
   desbordamiento horizontal, que las tablas quedan contenidas, que tarjetas y
   textos son legibles y que no hay errores de página, avisos de CSP ni cargas
   locales caídas. Verificado que detecta un estilo en línea inyectado.
3. **Retirar lo que quede de comparación**: pruebas con `?vista=anterior` o
   `load_project_reference` que sigan usando la referencia, y variantes
   `previous=True` de pruebas funcionales. Pendiente.
4. **Borrar `tests/reference`**, `tests/frontend/frozen/gen/`,
   `tests/e2e/frozen/gen/`, `gas_shim.js`, `reference_site` y el transporte
   `/api/rpc/` (`core/rpc/views.py`, `urls.py`, `access/rpc_policy.py`).
   **Conservar** el registro interno de `core/rpc/registry.py`
   (`register_rpc`, `get_rpc_function`): lo usan `warm_cache` y varios módulos.
   Pendiente.
5. **EVA**: retirar las 17 pruebas de `test_eva123` que describen el listado de
   cerrados retirado (`docs/eva-inventario-activo.md`). Antes confirmar con
   Christian si sus menús de columna y logos del histórico deben existir en la
   página nueva. Pendiente.
6. **KPIs de DM**: tres pruebas esperan C como cumplimiento y el código mezcla
   dos lecturas (la gráfica dice «cumplimiento en costo = 100% menos sobrecosto»;
   las tarjetas y la tabla definen C como % con avance > 100%). El usuario
   indicó «cumplimiento de costo», pero falta confirmar qué muestran tarjetas y
   tabla. No cambiar cálculo ni pruebas hasta tenerlo. Pendiente.
7. **Dos pruebas de referencia caducadas**: `test_approved_billability_layout`
   y `test_layout_keeps_approved_reference` de Capacidad diaria. Sus cajas
   cambiaron por las modificaciones aprobadas del 28/10 (plantilla por corte y
   desglose diario). Decidir si se retiran o se reemplazan por la prueba de
   humo. No regenerar sin revisar. Pendiente.
8. **Higiene**: línea larga en `sync_azure_history.py`, archivos sin formatear,
   suite completa, push (solo si el usuario lo pide).
9. **Documentación**: dejar `AGENTS.md` y el plan con un solo estado vigente.

## Qué NO hacer

- No congelar ni regenerar capturas del diseño actual para «hacer pasar» algo.
- No restaurar `?vista=anterior`, `_modern`, `anterior_disponible` ni
  `/api/rpc/` en producción.
- No borrar `core/rpc/registry.py`, `views.ejecutiva`, `views.comercial`,
  `dm_state`/`dm_rows` ni los servicios de caché.
- No formatear con `ruff format` sin lista de archivos: se aplica solo a los
  archivos propios (el 30/10 se reformatearon por error tres herramientas
  locales de `tools/migracion/`; solo cambió el formato).
