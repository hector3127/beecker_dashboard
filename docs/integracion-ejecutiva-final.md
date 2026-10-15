# Integración de Ejecutiva — 14 de octubre de 2026

Se integraron las funciones de Ejecutiva de `beecker_dashboard-main (6).rar`
en el proyecto local, conservando las correcciones operativas y de caché.

## Funciones incorporadas

- Ranking financiero de cuentas: sanas con margen mayor a 70%, no sanas
  con margen menor a 30%, e intermedias. Los costos pendientes o registros
  compartidos dejan la cuenta sin clasificación definitiva.
- Auditoría de todas las cuentas, búsqueda, filtros y acceso a costos por
  cuenta. El detalle de costos comprueba que el proyecto pertenezca a ella.
- Ingresos, margen y cobranza en el detalle de cuenta; asociación por ID de
  DataRevenue para cuentas con nombres regionales y contratos ROC visibles.
- Operations ejecutivo: Budget, avance en horas y ETC de proyectos con
  actividad en 2026. MPB para AER/T&M, Historico_Proyectos A:I para etapas y
  datos del proyecto, y Budget (Hrs) de J. El periodo operativo comienza en
  Discovery OP y termina en Completed/Cancelled. MME.002 conserva su periodo
  25/02/2026–22/06/2026.
- Revenue incluye Confirmed, Invoiced, Invoiced factoring, Collected y
  Collected factoring; excluye Forecast. Rentabilidad mensual limitada a 2026.
- Los detalles de proyecto muestran personas con horas de Clockify aunque
  no tengan asignación en Recursos. Las consultas de varios proyectos de una
  cuenta mantienen separadas sus entradas de horas.

## Cambios locales conservados

Se conservaron el contexto de tarifas y bandas compartido por la precarga,
los cortes de 24 horas con vigencia corta, el bloqueo de actualizaciones
concurrentes, los datos previos ante fallos de fuentes, los cálculos CR por
tarea y fechas, EVA-04, los KPIs con A:I más presupuesto J y la detección de
ROL/ID Clockify por encabezado. Panel anterior sigue retirado: Capacidad
instalada, proyectos y Facturabilidad por área conservan sus páginas propias.

## Precarga y validación

`python manage.py warm_cache` también prepara el ranking de cuentas y los
consumos del nuevo componente Operations de Ejecutiva. No requiere borrar
la caché existente. Los componentes preparados se renderizan desde sus
cortes; las cifras incompletas permanecen marcadas como provisionales.

Validación: 1,226 pruebas Python, cobertura 90.12%, 24 pruebas de interfaz,
revisión de Django y comprobación de Ejecutiva/Todas las cuentas en navegador.
La consulta real encontró 109 proyectos anuales y 51 cuentas; 3 proyectos
todavía no tienen Budget. Los costos pendientes se muestran explícitamente.

El respaldo previo del código está en
`tmp/integracion-companero-6/antes-integracion.zip`. Los archivos temporales
de comparación están fuera del control de versiones y no reemplazan la
configuración, credenciales ni datos del proyecto.
