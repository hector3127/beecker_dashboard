# Integración del RAR 8 — 16 de octubre de 2026

Se comparó `beecker_dashboard-main (8).rar` contra el proyecto vigente y el RAR 7.
La versión nueva ya contenía la mayoría de los ajustes de esta rama. Se importaron
sus diferencias funcionales, sin copiar configuración, credenciales, bases de
datos, entornos virtuales, archivos compilados ni cachés del archivo recibido.

## Mejoras integradas

- Costos desglosados por sprint/tareas, con personas, horas, bandas y tarifas.
  Los grupos particionan los registros del proyecto; no duplican sus horas.
  Los ingresos siguen perteneciendo al proyecto completo.
- Identificación explícita de tareas sin resolver y costos parciales.
- Resúmenes de auditoría preparados por cuenta y periodo, con detalle disponible
  para expandir sin consultas adicionales a Sheets o Clockify.
- Reutilización inmediata de costos preparados e invalidación del resumen cuando
  cambia un detalle. El botón Actualizar resumen omite su caché de cinco minutos.
- Consolidación de variantes S# sin ingresos independientes bajo su proyecto
  base, incluso si el base tampoco tiene ingresos.
- Conservación del periodo en los enlaces financieros de las cuentas y en los
  títulos de los rankings.
- Cobertura de Operations distingue consumos consultados de proyectos con
  presupuesto y consumo, e identifica proyectos sin Budget.
- Abrir un corte parcial ya preparado no reinicia consultas de costos pendientes.

## Decisiones conservadas

- Panel anterior sigue fuera de la navegación principal.
- Histórico conserva el alcance A:I y Budget J establecido en el proyecto;
  no se incorpora la lectura regional del bloque derecho propuesta en el RAR.
- El nombre genérico Arca Continental conserva su vinculación explícita con
  México; Perú sigue siendo una cuenta independiente.
- Se conserva el listado completo del servicio de cuentas no sanas y se limita
  solo su presentación a cinco filas, manteniendo el contador total.
- Se mantienen el diseño responsivo, el botón único de cuentas, las secciones
  agrupadas, los filtros, las rutas de regreso y la selección mensual de
  facturabilidad. Los DMs con puntos aislados siguen fuera de la gráfica.
- La actualización en segundo plano conserva la propiedad de sus consultas;
  no se agrega una consulta paralela adicional al abrir el resumen de Operations.

Las claves financieras y de costos pasan a v9. La primera preparación puede
necesitar reconstruir los detalles con los nuevos datos de sprint.

## Validación

- 451 pruebas del portal aprobadas con fuentes simuladas (`--no-cov`).
- Suite JavaScript completa y prueba específica de expansión local de sprints.
- Comprobación de Django, formato y revisión de diferencias.
- No se modificaron las fuentes de datos reales.
