"""Conceptos ejecutivos y validaciones de negocio."""

# ruff: noqa: E501

CONCEPTS = [
    (
        "Periodo",
        "Rango inclusivo Desde–Hasta; se aplica a facturación, costos, consumo y booking. El título muestra las fechas exactas.",
        "Calendario ejecutivo",
    ),
    (
        "Importes",
        "Dólares estadounidenses. K = miles, M = millones, B = mil millones (convención estadounidense). Miles sin decimales; millones y mil millones con hasta dos decimales de escala. Truncado solo de presentación; cálculos con precisión original. Ejemplo: 1,897,644.14 → 1.89M.",
        "Financiero y Comercial",
    ),
    (
        "Facturación",
        "Invoiced + Invoiced Factoring + Collected + Collected Factoring, según DataRevenue G/H. Confirmed queda fuera. Las fechas y el corte contable requieren validación con Florencia.",
        "Pendiente de validación contable",
    ),
    (
        "Revenue contratado",
        "Confirmed + los estados facturados y cobrados. No equivale a facturación ni al booking comercial. Se conserva en la auditoría de proyectos.",
        "DataRevenue",
    ),
    (
        "Booking / ventas cerradas",
        "Suma de oportunidades ganadas del rango, convertidas a dólares según el tipo de cambio disponible. No es facturación.",
        "Backlog_Proyectos",
    ),
    (
        "Cobranza",
        "100 × Collected (incluido factoring) ÷ (Invoiced + Collected, incluido factoring). Se usa la fecha disponible de DataRevenue G. Sin denominador se muestra Pendiente. No es una conciliación bancaria ni un cohort de facturas hasta validar fechas con Florencia.",
        "DataRevenue · validación pendiente",
    ),
    (
        "Costos",
        "Horas del periodo × tarifa de banda; deduplicación por ID de registro Clockify. Falta de bandas o tarifas implica costos incompletos.",
        "Clockify + Bandas/rol + Master rates",
    ),
    (
        "Utilidad bruta",
        "Facturación del periodo − costos del periodo. Un proyecto sin facturación conserva sus costos y reduce la utilidad de su cuenta.",
        "Cálculo financiero",
    ),
    (
        "Margen bruto",
        "100 × utilidad bruta ÷ facturación. No se calcula porcentaje con facturación cero ; con costos incompletos se muestra un margen parcial con asterisco y pendientes.",
        "Cálculo financiero",
    ),
    (
        "Rentabilidad mensual",
        "Facturación agrupada por mes de la fecha disponible, frente a costos por fecha de cada registro. No se atribuye la facturación total del proyecto a cada mes.",
        "Facturación mensual pendiente con Florencia",
    ),
    (
        "Comparación de cuentas",
        "En Business Overview se elige facturación, utilidad bruta o margen bruto, sin ponderación 70/30. Se comparan todas las cuentas del corte con dato para ese indicador, se separan en mitad superior e inferior y se muestran hasta 5 por grupo. La búsqueda limita las cuentas comparadas; cada encabezado permite invertir el orden dentro del grupo. Un porcentaje no aplicable no equivale a cero. * indica costos y márgenes parciales. Los nombres de los grupos representan posiciones relativas, no una evaluación integral de salud.",
        "Corte financiero del periodo · base contable pendiente",
    ),
    (
        "Tarifa de costo vendida (costing rate)",
        "Tarifa de costo considerada al vender una oportunidad. Su fuente, unidad y regla de asignación están pendientes de validación con Florencia. Se muestra Pendiente; no se deduce de revenue dividido entre horas ni se sustituye por la tarifa interna de banda.",
        "Pendiente de fuente y validación con Florencia",
    ),
    (
        "Tarifa interna de banda",
        "Tarifa de costo por hora asociada a la banda del recurso en Master rates. Se utiliza junto con las horas registradas para calcular los costos disponibles. No equivale a la tarifa de costo con la que se vendió una oportunidad.",
        "Bandas/rol + Master rates",
    ),
    (
        "ETC",
        "Presupuesto de horas − horas consumidas de los proyectos del rango con ambas medidas. Un ETC negativo señala sobreconsumo. No se publica un total como completo si faltan proyectos o presupuestos.",
        "Población operativa + Clockify",
    ),
    (
        "FTE equivalente",
        "ETC ÷ número de meses calendario del rango ÷ 360. Mes: ETC/360; trimestre: ETC/3/360. Base 360 solicitada por Dirección; no es un calendario laboral estándar.",
        "Conversión operativa de referencia",
    ),
    (
        "Avance en horas",
        "100 × consumo ÷ presupuesto; es avance de consumo presupuestal, no porcentaje de entregables terminados. Presentación sin decimales.",
        "Población operativa",
    ),
    (
        "Facturabilidad global",
        "100 × horas facturables ÷ capacidad del equipo. Misma fuente GSE, plantilla y especialidades que Facturabilidad en Operativa; rango seleccionado, sumando horas y capacidad de los meses disponibles hasta la fecha de corte; no es un promedio de porcentajes. * indica cobertura parcial.",
        "Clockify · corte preparado",
    ),
    (
        "Inversión operativa",
        "Suma de horas con etiqueta INV_OPERATIVA del rango, sin duplicar registros. Se presenta en horas enteras.",
        "Clockify",
    ),
    (
        "Trabajo por entregar",
        "Regla vigente: suma de importes Confirmed de DataRevenue H con fecha G futura respecto al día del corte y dentro del periodo seleccionado. Es revenue futuro previsto; no equivale a tareas pendientes ni a facturación. Si falta el corte se muestra Pendiente.",
        "DataRevenue G/H · regla del corte comercial",
    ),
    (
        "Previas al cierre",
        "Regla vigente: importe en USD de oportunidades abiertas únicas de Backlog_Proyectos con fecha de cierre dentro del periodo seleccionado. No representa ventas ganadas ni facturación; la cifra se consulta con el alcance del corte comercial.",
        "Backlog_Proyectos · oportunidades abiertas únicas",
    ),
    (
        "Decisiones y seguimiento",
        "Acuerdos capturados de Dirección o Consejo con cuenta, fecha de sesión, compromiso y estado. No se alimenta automáticamente con alertas técnicas ni nombres de BM/DM. Registros antiguos sin sesión se identifican para clasificación.",
        "Registro local de acuerdos",
    ),
    (
        "Corte fijo",
        "La página abre datos preparados sin llamadas individuales a Clockify. La actualización ocurre en segundo plano; la primera carga y cada actualización solicitada se muestran una sola vez al terminar la preparación. No hay cifras provisionales que cambien en pantalla.",
        "Caché por rango",
    ),
]

CONCEPTS.append(
    (
        "Margen vendido vs. real por oportunidad",
        "Cruce por DataRevenue B/C, reuniendo todos sus Project IDs de E. Margen vendido = I; margen real = 100 × (revenue de H − costos disponibles) / revenue. Incluye los estados de Finanzas, incluso Confirmed, separado de facturación. Desviación = real − vendido en pp. Solo en esta comparativa se excluyen licencias, SaaS y especializados. Costos parciales marcados con *. IDs compartidos entre oportunidades requieren asignación validada; no se duplica su costo. No se elige un margen arbitrario cuando I presenta valores distintos.",
        "DataRevenue C/E/G/H/I · Clockify · tarifas internas de banda",
    )
)
