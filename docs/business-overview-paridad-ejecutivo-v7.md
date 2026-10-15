# Business Overview y Ejecutivo del RAR 7

Comparación funcional de `beecker_dashboard-main (7).rar` con Business Overview.
Se conserva la presentación responsiva del proyecto, su navegación y la caché.

| Función del RAR | Integración |
| --- | --- |
| Calendario doble, rangos rápidos y fechas personalizadas | Disponible; conserva fechas al navegar y separa las cachés por periodo. |
| Ingresos, margen bruto y cobranza | Disponible con las mismas fuentes y estados financieros. |
| Budget, consumo/avance y ETC | Disponible; conserva la precarga y el tratamiento de datos parciales. |
| Ventas cerradas y oportunidades abiertas | Disponible desde Comercial real; no inventa saldo por entregar cuando falta. |
| Barras mensuales de ingresos/costos y curva de margen | Disponible; incorpora porcentajes visibles como el RAR cuando el espacio permite leerlos. Mantiene cortes de línea ante meses sin margen y valores negativos. |
| Top 5 cuentas sanas y no sanas | Disponible; presenta hasta cinco por bloque y permite ir al listado completo. No recorta los datos del servicio de cuentas. |
| Pérdidas sin ingresos y márgenes provisionales | Disponible en las tablas financieras. |
| Detalle de costos por proyecto, personas y tarifas | Disponible; incluye ingresos/margen y actualiza resultados parciales. |
| Separación de variantes S# y proyectos sin ingresos | Integrada en el inventario financiero y los costos. |
| Tabla única de decisiones, acuerdos y pendientes | Disponible; búsqueda, estado y formulario para crear/editar seguimiento. |
| Crear seguimiento desde una decisión | Precarga proyecto, responsable y acción sugerida; guardar requiere pulsar Guardar. |

No se sustituyeron los enlaces reales por los enlaces de ejemplo del RAR ni se
restauraron sus consultas duplicadas en primer plano. En móvil y tablet las
tablas se adaptan a registros etiquetados; las gráficas conservan escala y datos.

Validación: pruebas del portal y JavaScript de calendario, gráfica, seguimiento
y componentes financieros. Vista previa con datos de referencia en
`design/executiva-propuesta/revision-actual/`.
