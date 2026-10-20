# Comparativa solicitada por Florencia

La vista /ejecutiva/oportunidades/ compara el margen comercial vendido con el real por oportunidad (DataRevenue C) y cuenta (B). No se toma la oportunidad más reciente de un Project ID: una oportunidad puede contener varios IDs operativos (E), y un ID compartido no permite asignar costos automáticamente.

- I: Gross Margin Comercial, admite porcentajes en texto o fracciones numéricas; un cero explícito se conserva.
- G/H: fecha y revenue del periodo, considerando Confirmed, Invoiced, Invoiced Factoring, Collected y Collected Factoring. Confirmed se muestra separado de lo ya facturado.
- Margen real: (revenue del periodo − costos disponibles) / revenue del periodo × 100.
- Desviación: margen real − margen vendido, en puntos porcentuales.
- Las filas repetidas de cobros no suman porcentajes. La oportunidad debe tener el mismo margen vendido; valores distintos se señalan para validación, no se elige una fila arbitraria.
- Solo esta comparativa excluye servicios identificados como licencias, SaaS y especializados. Las otras vistas conservan su alcance, conforme a la confirmación del usuario.
- Costos: horas Clockify por tarifa interna de banda, conservando horas facturables, no facturables y sin task. No se sustituye por la tarifa comercial.
- CR y sprints sin registro financiero independiente pertenecen al ID puro. El desglose sigue disponible por proyecto.
- Se deduplican costos por ID de registro Clockify dentro de la oportunidad. Un Project ID compartido entre oportunidades queda sin asignación y marcado como parcial; no se reparte sin una regla validada.
- Sin costos disponibles no se publica un margen de 100%. Con parte del costo disponible, el margen y la desviación se marcan con asterisco.

## Validación pendiente con Finanzas

No se alteran IDs mal capturados ni se inventan vínculos de ROC. Los servicios históricos reunidos en ROC.001 requieren trazabilidad por oportunidad/cuenta para asignar sus costos. Las tarifas individuales que no correspondan a una banda requieren una fuente validada; no se estiman. Las reclasificaciones de Overall, SLC y Femsa requieren la actualización de la fuente de Finanzas.

En la comprobación inicial de enero–septiembre de 2026 se leyó la columna “Gross Margin Comercial” y se encontraron 270 oportunidades con margen comercial. El revenue calculado fue 2,386,769.35, por lo que no se declara conciliado contra la referencia aproximada de 1.8 millones de la reunión. Los servicios genéricos y los costos pendientes requieren revisión con Florencia. Ningún importe se ajustó para forzar coincidencia.
