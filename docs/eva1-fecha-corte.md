# EVA 1: fecha de corte (27/10/2026)

Cambio solicitado por el usuario para consultar proyectos abiertos en un día,
incluyendo suspendidos/vencidos, en vez de filtrar por solapamiento Start–Finish.

Actualización posterior: el usuario confirmó los KPIs T/C por cumplimiento.
EVA 1 usa ahora corte menos Finish (negativo antes del vencimiento y positivo
después). La convención del cargador compartido para otras pantallas no cambia.
Ver [reglas de KPIs](kpis-dm-reglas.md).
Una fecha consultada explícitamente, incluso hoy, usa la reconstrucción
compartida con KPIs. Solo la entrada sin `corte` conserva el resumen actual.

## Uso y alcance

En `/operativa/eva-1/`, elegir **Fecha de corte** y **Consultar corte**.
La URL conserva `corte=AAAA-MM-DD`, `manager`, `service` y el origen `volver`.
Los selectores DM/servicio recargan los datos del corte aplicado; editar la
fecha exige consultar para evitar peticiones por cada dígito del calendario.
Las tarjetas y ambos pivotes aplican el mismo DM/servicio que el detalle.
Los menús por columna siguen siendo filtros locales de la tabla y del CSV.

La entrada sin corte conserva el cargador existente y sus datos de Azure.
Las fechas consultadas usan `apps/portal/services/eva_cut.py`:

- Inventario por ID exacto desde los eventos A:I de `Historico_Proyectos`,
  incluso cuando el ID dejó de existir en `Proyectos`. Servicio, nombre y
  cuenta del evento, con catálogo vigente de respaldo. No unir `_S2`/`_CR`
  con un ID base para forzar la coincidencia con un correo.
- Etapa/vigencia con el resolutor existente, evaluado al corte. Se excluyen
  estados terminales con fecha menor o igual al corte (cierre del día).
  Un terminal sin fecha se excluye por no poder ubicarlo temporalmente.
  Finish vencido por sí solo no cierra el proyecto. Se incluyen suspendidos.
- DM del último evento con Start no posterior al corte y del ID exacto.
  No se toma el primer DM del histórico ni el de otra nomenclatura.
  No se fusionan nombres distintos sin una regla de alias confirmada.
- Presupuesto de J del último evento fechado hasta el corte que lo tenga,
  con `Proyectos.Budget_Hrs` como respaldo. No sumar presupuestos repetidos
  entre etapas. **Esto es una reconstrucción desde la hoja sincronizada,
  no una versión archivada del presupuesto original.**
- Clockify usa rango explícito desde el primer Start hasta el corte, con
  fecha local inclusiva. Conserva deduplicación, horas facturables y reglas
  existentes de pertenencia a nomenclatura. No usa el Finish actual como
  límite de las horas de un proyecto vencido. Errores/fechas ausentes se
  marcan pendientes; faltantes no entran al promedio de avance.
- No se consulta Azure actual como si fuera histórico. Sus 12 columnas de
  tareas y riesgos se muestran **Pendiente** para días pasados, también CSV.
- ETC y desviación de horas conservan presupuesto menos consumo. No se
  implementó la fórmula desconocida del ETC del correo (ejemplo AMK.012).

El histórico plegable de cerrados conserva su consulta actual independiente;
no es una lista de cierres reconstruidos al corte.

## Conciliación local de IDs, sin consultar proveedores

Con la copia local de Proyectos/Histórico sincronizada el 21/10, la nueva
selección al 29/01/2026 devuelve 20 IDs; el detalle del correo pegado tiene
22. Solo se contrastó inventario y responsables en esta comprobación, no
horas ni tareas. No se insertaron valores del correo en la aplicación.

IDs del correo ausentes en la selección local:
`AMK.009`, `AMK.012`, `CAG.001`, `DAP.004`, `MCC.016`, `MCC.023`,
`NSC.B.003`, `NSC.C.007`, `SBM.020`.

IDs adicionales seleccionados del histórico local:
`AMK.009_S2`, `AMK.012_CR`, `DAP.004_CR`, `MCC.016_CR`, `MCC.023_S2`,
`NSC.B.003_S2`, `NSC.C.007_S1`.

Se requiere contrastar los eventos/IDs y el script original del reporte con
Gera. Una copia sincronizada actual no garantiza reproducir un correo viejo:
pueden haber cambiado fechas, responsables, presupuestos y nomenclaturas.
