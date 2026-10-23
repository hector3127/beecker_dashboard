# Horas mensuales por cuenta

Desde una cuenta, el enlace **Ver horas por mes** abre una matriz de proyectos y meses con selector de año o rango de fechas, selección múltiple de proyectos, totales y descarga CSV para Excel. El año actual llega hasta el mes en curso, marcado con asterisco; los años anteriores muestran doce meses.

En **Periodo → Rango de fechas** se eligen Desde y Hasta y se pulsa Generar reporte. Ambas fechas se incluyen; los rangos pueden cruzar años y abarcar hasta tres años. No se incluyen registros futuros. Los meses se etiquetan con su año cuando el rango cruza de año, y los meses recortados se marcan con asterisco.

El desplegable de proyectos permite buscar por ID o nombre y marcar uno o varios. **Mostrar todos** elimina esa selección. La búsqueda únicamente acota las opciones del selector; las casillas determinan las filas del reporte. Las tarjetas, el total mensual y el CSV se recalculan con los proyectos elegidos. Las fechas y la selección se guardan en la URL y se conservan al abrir un proyecto y regresar.

La pantalla nueva usa `frontend/templates/pages/account_hours.html`, CSS y JavaScript separados. Django prepara el reporte en `account_hours.py` y lo entrega en `GET /api/v1/screens/cuenta/horas/?nombre=…&anio=…`. `descargar=csv` entrega la misma población y cifras. Ambos exigen `view_operations` y validan el alcance de cuenta antes de consultar las fuentes. La página conserva el regreso a la cuenta, y los proyectos regresan al reporte con su año.

Las horas proceden exclusivamente de `ClockifyTimeEntry` guardado y de los meses de `ClockifyMonthSync`; abrir la pantalla no descarga datos externos de Clockify ni consulta tarifas. La fecha usada es la fecha de trabajo local guardada, no la fecha del ingreso o de la factura. Se incluyen horas facturables y no facturables.

El inventario parte del mismo de costos e ingresos (MPB, Histórico y DataRevenue). Se agregan IDs sin ingresos, como inversión, cuando el catálogo normalizado los vincula explícitamente con la cuenta y tienen registros en el año. No se atribuyen proyectos por una mera coincidencia del prefijo. Las variantes no independientes permanecen agrupadas en el proyecto base, como en costos.

Se reutiliza el resolvedor de vínculos de Clockify. Las variantes S/CR independientes y los contratos AER/ROC mensuales se separan antes de sumar; cada registro se cuenta una sola vez. Vínculos ambiguos, tareas sin identificar, IDs compartidos entre cuentas y meses no sincronizados se señalan como pendientes o parciales. No se convierten en ceros. Los totales parciales suman únicamente horas identificadas.

Sin selección de proyectos los totales y la descarga corresponden a toda la cuenta; con selección corresponden a ese subconjunto. El endpoint acepta `desde`/`hasta` y parámetros `proyecto` repetidos, y valida que todos pertenezcan al reporte autorizado antes de exportar. La última sincronización se muestra en pantalla; el corte del mes actual no implica que sus horas estén actualizadas al minuto.

## Comprobación de Oxxo

Con la base guardada al desarrollar esta vista, enero–octubre de 2026 tiene diez IDs agrupados y 6,843.3834 horas. Incluye CCO.000 con 77.5 horas de inversión. Octubre está abierto; sus registros corresponden a la última sincronización disponible, no a un cierre mensual.

Estos valores son una comprobación de implementación, no una conciliación financiera ni un compromiso de que futuros cortes permanezcan iguales. La cuenta operativa puede mostrar otro número de filas porque separa sprints y presenta consumos acumulados de sus contratos.
