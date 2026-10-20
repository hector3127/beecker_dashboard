# Ajustes solicitados por Dirección · 19/10/2026

Implementados en el proyecto local:

- Presentación monetaria compartida en financiero y comercial, truncada a miles sin centavos; una indicación de moneda por vista.
- Facturación separada del revenue contratado y booking; estados Invoiced/Collected, incluido factoring.
- Cobranza documentada, con las limitaciones de la fecha Revenue disponible.
- Comparación mensual por mes del registro de facturación disponible y fecha del costo, sin prorratear el valor del proyecto.
- Ranking 70/30 confirmado: margen ponderado por volumen y facturación. Grupos sin cuentas duplicadas.
- ETC y avance en dos mitades, después facturabilidad e inversión operativa. Horas y avance sin decimales; conversión FTE con base 360 por mes.
- Página principal sin lecturas de fuentes al renderizar: corte fijo preparado y actualización explícita en segundo plano. Los márgenes con costos incompletos no se publican.
- Decisiones originadas en Dirección/Consejo, agrupadas por cuenta, fecha de sesión y compromisos. Se mantienen los registros antiguos para clasificarlos, sin introducirles una sesión ficticia.
- Diccionario de datos disponible en la app y docs/diccionario-datos-ejecutivo.md.

## Validaciones expresamente pendientes

- Florencia: validar fuente/fecha de facturación mensual y fechas de cobro. DataRevenue G es la fecha disponible, no una fecha contable verificada.
- Poly: fuente y fórmula del saldo de trabajo por entregar.
- Luis Enrique: categoría de oportunidades previa al cierre y su uso para capacidad.

No se contactó a estas personas ni se inventaron datos de sus fuentes.

## Verificación

- Calendario probado en navegador: Desde 01/05/2026, Hasta 31/10/2026; selección y URL conservan ambas fechas.
- Apertura HTML local medida: 0.063 segundos. Es tiempo de renderizado, no de regeneración de todas las fuentes.
- 28 pruebas de backend y 16 de frontend correctas en los conjuntos relevantes.
- Migración local portal.0002_executiveagreement_meeting aplicada; sin migraciones pendientes.

La generación del primer corte de un rango todavía depende de Sheets/Clockify. Los IDs sin vinculación y las tarifas faltantes se conservan como pendientes y no se presentan como cifras completas.
