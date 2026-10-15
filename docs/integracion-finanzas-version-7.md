# Integración financiera del RAR 7

Se comparó `beecker_dashboard-main (7).rar` con el proyecto existente y se
integraron únicamente sus cambios financieros. No se importaron cachés,
credenciales, configuración, bases de datos ni archivos compilados del RAR.

## Cambios

- El detalle de costos muestra ingresos por Project ID y margen porcentual.
  Cuando no hay ingresos, muestra el resultado en USD sin inventar un porcentaje.
- Los ingresos usan DataRevenue E/G/H, los estados válidos y el periodo elegido;
  el detalle por cuenta conserva su filtro de cuenta.
- El inventario financiero incorpora proyectos operativos de MPB e
  Historico_Proyectos que se solapan con el periodo, aunque no tengan ingresos
  registrados. Sus costos afectan la rentabilidad de la cuenta.
- Una cuenta con costos completos y sin ingresos se clasifica como no sana.
  Las cuentas con costos incompletos o registros compartidos siguen pendientes.
- Las variantes S# registradas separadamente en DataRevenue se calculan con sus
  tareas. El proyecto base excluye esas mismas tareas para evitar duplicarlas.
  Las variantes sin registro financiero independiente se mantienen bajo el base.
- Consultar el desglose actualiza horas, costo, margen, estado y resumen global.
  Si la consulta resuelve un error anterior, el enlace al proyecto se habilita.

## Ajustes conservados

Se conservan Business Overview, la vista responsiva, el gráfico mensual actual,
los botones de regreso con su origen y filtros, los avisos al pulsar IDs con error,
la actualización en segundo plano y la reutilización de costos precalculados.
El listado de cuentas no sanas mantiene todas las cuentas elegibles.

La relación histórica de cuentas usa exclusivamente A:I, conservando la regla
del proyecto; no utiliza el bloque derecho de la hoja que consulta el RAR.
Las claves de costos y del corte financiero se versionaron para no reutilizar
resultados calculados con el inventario anterior. El siguiente cálculo preparará
los costos con el nuevo alcance; puede tardar más en ese primer recorrido.

## Validación

- 438 pruebas de `tests/portal` aprobadas (`--no-cov`, suite del portal).
- Pruebas JavaScript de finanzas, actualización de costos y navegación.
- `manage.py check` sin incidencias.
- Pruebas con fuentes simuladas: sin consultar ni modificar las hojas reales.
