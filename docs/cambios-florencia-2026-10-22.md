# Cambios de Florencia en la comparativa de márgenes

Fuente: transcripción de Dashboard Managment del 21/10/2026, intervenciones de Florencia aproximadamente entre 00:20 y 00:30.

## Solicitud e implementación

- Revenue → **Bookings**: valor reconocido total de la oportunidad en DataRevenue, agrupado por cuenta y nombre de oportunidad, sin limitarlo al rango. Se conservan los estados financieros admitidos y las exclusiones de servicios existentes; cancelaciones y subtotales no se incorporan.
- **Revenue operado**: nueva columna. Por autorización del usuario se toma provisionalmente Fecha Revenue Ajustado (G) como fecha del servicio. Suma H en el rango seleccionado y hasta el día actual, incluso Confirmed. No prorratea por días ni estima ingresos a partir de horas. `operated_revenue_status=assumed_service_date_g` permite identificar esta suposición al migrar.
- **Cobrado**: nueva columna, exclusivamente Collected y Collected Factoring. El cálculo separado ya existía; ahora se muestra.
- **Facturado** permanece explícito e incluye Invoiced y Collected, incluidos Factoring. Facturado y Cobrado se filtran por G, no por una fecha independiente de factura o pago; esta limitación queda visible.
- Costos disponibles → **Costos**.
- Margen consumido → **Margen real**, incluido el título y la tarjeta de promedio.
- Se conserva margen vendido y desviación en puntos porcentuales.

La fórmula de margen se mantiene: (revenue del rango − costos del rango) / revenue del rango. El revenue del rango incluye los estados financieros admitidos, incluso Confirmed y fechas futuras dentro del rango, como antes. No se sustituye su denominador por Bookings total, Cobrado ni la nueva aproximación de revenue operado. La explicación lo indica para evitar confundir las bases.

## Pendiente de Finanzas

Confirmar que G es efectivamente la fecha de prestación del servicio; cambiar el nombre no acredita esa equivalencia. Florencia también propuso compartir un costing rate por empleado y mes, incluyendo cargas sociales. Esto requiere identificar y validar esa nueva fuente; los costos siguen usando la tarifa interna de banda. No se modifica el costing rate con datos supuestos.

Florencia informó que ya había corregido registros financieros desfasados al filtrar solo una de dos partes de su archivo. No se replican correcciones manuales ni se alteran registros locales para forzar la coincidencia.

## Compatibilidad con la migración

La fase 7 aún no está migrada. Se actualiza su pantalla vigente y su servicio Django, añadiendo `bookings`, `operated_revenue` y `operated_revenue_status` sin renombrar claves existentes (`revenue`, `invoiced`, `collected`, `cost`, `actual_margin`). La versión del corte de oportunidades sube a 6 para no reutilizar resultados sin las columnas nuevas. Las reglas, permisos y páginas ya migradas permanecen en su estructura actual.

La fase 7 debe transportar estos campos a la API y al frontend modular, conservando la nota provisional sobre G y la navegación de regreso. La prueba de cuenta → comparativa → cuenta y su referencia visible se actualizan con los nuevos encabezados.

## Verificación

33 pruebas de servicios y vistas aprobadas. Se actualizó la referencia esperada de la comparativa para la fase 7. El recorrido en navegador quedó sin ejecutar: Playwright no encontró su ejecutable Chromium instalado. La validación visual y de ese recorrido sigue pendiente; no se declara completada por las pruebas de servicios.
