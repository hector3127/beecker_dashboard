# KPIs de DM: reglas confirmadas el 27/10/2026

Solicitud del usuario: construir los KPIs a partir de EVA 1. Sustituye para
esta pantalla las fórmulas anteriores de desviación media y consumo medio.
No modifica los indicadores generales de Operativa ni de otros servicios.

## Corte e inventario

- Mes cerrado: último día de lunes a jueves de ese mes. Viernes, sábado o
  domingo retroceden al jueves. No se aplica un calendario de festivos.
- Ejemplos 2026: enero 29, febrero 26, mayo 28, agosto 31, septiembre 30.
- Mes actual: corte provisional hasta el último lunes–jueves disponible,
  nunca futuro. Si aún no existe uno en el mes, no se inventa un corte del
  mes anterior bajo la etiqueta del mes nuevo.
- TP: todos los IDs abiertos del DM al corte de EVA 1, incluidos suspendidos
  y vencidos, excluidos terminales al corte. Se usa `eva_cut.cut_rows`, con
  el mismo inventario exacto, histórico de responsables y presupuesto.
  No se agregan AER/T&M de MPB a este universo de EVA 1.

Para comparar, usar **Consultar corte** en EVA 1, también si se elige hoy:
ese modo comparte el presupuesto histórico J y los IDs con los KPIs.
La entrada sin parámetro `corte` conserva la consulta actual anterior
(presupuesto de Proyectos/Azure actual). En la base local actual hay
presupuestos distintos entre ambas fuentes, por ejemplo Oxxo; no se
cambiaron registros para ocultar la diferencia.

## Porcentajes

- Desviación EVA 1 = corte menos Finish: negativo antes del vencimiento,
  cero el día de Finish, positivo si está vencido. La inversión de signo
  solo se aplica en EVA 1; el cargador compartido conserva su convención
  anterior para otros consumidores.
- T = número de proyectos con desviación <= 0 / TP × 100.
- C = número de proyectos con Project Advance <= 100 / TP × 100.
- Se incluyen los límites 0 días y 100%. Los valores no se promedian.
- Total del equipo: suma de cumplimientos / suma de proyectos. No es la
  media de porcentajes de DM con cargas diferentes.
- Falta de Finish, presupuesto positivo u horas verificadas: TP se conserva;
  el porcentaje afectado queda pendiente. No se reduce el denominador ni
  se clasifican faltantes como cumplimiento o incumplimiento.
- Sin proyectos: TP=0, T/C sin dato. Cero cumplimiento conocido sí es 0%.
- Se conserva precisión al calcular; se redondea en la presentación.

Ejemplo: 6 proyectos; 4 con desviación <=0 y 3 con avance <=100:
TP=6, T=66.7%, C=50% en pantalla.

## Presentación y contratos

Tarjetas, tabla principal, históricos y gráfica presentan los nuevos
porcentajes. Los trimestres conservan la regla previa de promedio de los
meses disponibles; ahora promedian porcentajes de cumplimiento mensuales.
La mejor/peor proporción sigue ordenándose por T; sin DM no participa.

«Fuera de tiempo» y «Fuera de costo» son conteos independientes, con las
claves API `time_late` y `cost_over`; pueden solaparse. No representan la
clasificación RAID de proyectos. Las claves antiguas de salud se conservan
por compatibilidad, pero estas columnas ya no las interpretan como costos.
La API declara `metrics.basis=eva1_compliance`, T/C en porcentaje y días de
corte 0–3 (lunes–jueves). Internamente se conserva el contenedor TimeCost
para matrices/trimestres; `time_days` transporta T (%) solo en estos KPIs.

Pipeline activo: `load_kpi_history` → `kpi_eva.build_eva_history` →
`eva_cut.cut_rows`. Los helpers genéricos previos de KPIs no deciden el
inventario ni las fórmulas de esta pantalla. La caché usa una clave nueva
por regla/año/día para no reutilizar los antiguos promedios.

Las diferencias de datos del correo siguen pendientes: nuevas reglas no
equivalen a recuperar versiones históricas borradas o modificadas de las
hojas. Ver [EVA 1 por fecha de corte](eva1-fecha-corte.md).
