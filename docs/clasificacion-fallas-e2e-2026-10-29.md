# Clasificación de las fallas e2e (29/10/2026)

Suite completa sobre `bfce48a`: 3,071 aprobadas, 630 fallidas, 44 errores,
1 omitida (1 h 12 min). Fuera de `tests/e2e` no falla nada (portal, core,
access, clockify, capacidad, datastore y API); 478 Node aprobadas. Ningún
cambio de aplicación en esta revisión.

## Causas

1. **~630 comparaciones del detalle de proyecto contra la referencia anterior**
   (`*_match_previous`, `test_unchanged_shared_view`, `test_model_keeps_shared_view`,
   `test_entry_matches_previous`, `test_session_messages_match_previous`,
   `test_generic_timeline_model_preserves_the_existing_modern_view`, etc.). Esa
   pantalla se rediseñó a pedido del usuario (`docs/diseno-proyectos.md`); la
   referencia vieja ya no es el objetivo. Se resuelven congelando el diseño
   actual como línea base (como Ejecutivo AER y Recursos AER), no regenerando
   expectativas ante un fallo.
2. **44 errores de preparación en `test_eva123`**: el parche
   `views.load_eva2_closed` ya no existe (`d95f31a` lo vuelve opcional). Con eso
   corren 27 pruebas vigentes.
3. **17 pruebas de `test_eva123` describen el listado de cerrados retirado**
   (`docs/eva-inventario-activo.md`): referencia aprobada de EVA 1, filtros/CSV
   del histórico, errores de fuente, tablas de EVA con menús de columna y logos
   en el histórico. La página nueva muestra «Todavía no hay un inventario
   guardado» y no tiene `#eva-closed-box`. Requieren decisión: retirar o
   reescribir sobre el inventario (`tests/e2e/test_eva_native.py` cubre filtro,
   exportación, actualización y nota de horas).
4. **3 pruebas de KPIs de DM (`test_ejecutiva_kpis`)** esperan la definición
   anterior de C («avance ≤ 100% / TP») y sus valores. Antes de actualizarlas
   hay que confirmar la definición vigente de C (cambió el 28/10 y de nuevo en
   `bfce48a`); no ajustarlas al comportamiento actual sin esa confirmación.
