"""Definiciones y cálculos aprobados para los indicadores de Dirección."""

# (indicador, definición, categoría, cálculo)
INDICATORS = [
    (
        "Facturación",
        (
            "Importe de los registros facturados o cobrados del periodo, "
            "incluidos los de factoraje."
        ),
        "Financieros",
        "Suma de importes facturados y cobrados, incluido factoraje.",
    ),
    (
        "Importe cobrado",
        (
            "Importe de los registros con estado cobrado, incluidos los "
            "de factoraje."
        ),
        "Financieros",
        "Suma de importes cobrados del periodo, incluido factoraje.",
    ),
    (
        "Porcentaje de cobranza",
        "Importe cobrado como porcentaje de la facturación del mismo corte.",
        "Financieros",
        "Importe cobrado ÷ facturación × 100. Sin facturación: no disponible.",
    ),
    (
        "Ingresos contratados",
        (
            "Importe de los registros confirmados, facturados o cobrados. "
            "Se consulta en el detalle financiero o de proyectos."
        ),
        "Financieros",
        (
            "Suma de importes confirmados, facturados y cobrados, "
            "incluido factoraje."
        ),
    ),
    (
        "Ingresos confirmados futuros",
        (
            "Importe confirmado con fecha posterior al corte y dentro del "
            "periodo seleccionado."
        ),
        "Financieros",
        (
            "Suma de importes confirmados cuya fecha es posterior al "
            "corte y está entre Desde y Hasta."
        ),
    ),
    (
        "Costo de horas registradas",
        (
            "Costo de las horas registradas en el periodo, calculado con "
            "la tarifa interna de cada banda."
        ),
        "Financieros",
        "Suma de horas de cada registro único × tarifa interna de su banda.",
    ),
    (
        "Utilidad bruta",
        (
            "Facturación del periodo menos costos del periodo, expresada "
            "en dinero."
        ),
        "Financieros",
        "Facturación − costos del periodo.",
    ),
    (
        "Margen bruto",
        "Utilidad bruta como porcentaje de la facturación del periodo.",
        "Financieros",
        "Utilidad bruta ÷ facturación × 100. Sin facturación: no disponible.",
    ),
    (
        "Cobertura de costos",
        (
            "Proyectos con costos completos, parciales o faltantes, sobre "
            "el total incluido en el cálculo."
        ),
        "Financieros",
        (
            "Cantidad de proyectos por estado de cobertura ÷ total de "
            "proyectos incluidos × 100."
        ),
    ),
    (
        "Margen vendido",
        "Porcentaje de margen registrado al vender la oportunidad.",
        "Financieros",
        (
            "Margen registrado en la venta. Si existen valores "
            "contradictorios: pendiente de validación."
        ),
    ),
    (
        "Margen real por oportunidad",
        (
            "Porcentaje que queda tras restar los costos disponibles a "
            "los ingresos considerados para la oportunidad, incluidos los "
            "confirmados."
        ),
        "Financieros",
        (
            "(Ingresos de la oportunidad − costos disponibles) ÷ ingresos "
            "de la oportunidad × 100."
        ),
    ),
    (
        "Desviación de margen",
        "Margen real menos margen vendido, en puntos porcentuales.",
        "Financieros",
        "Margen real − margen vendido (pp).",
    ),
    (
        "Ventas ganadas (booking)",
        (
            "Importe en USD de las oportunidades ganadas en el periodo "
            "seleccionado."
        ),
        "Comerciales",
        "Suma de importes en USD de oportunidades ganadas en el periodo.",
    ),
    (
        "Importe de oportunidades abiertas",
        (
            "Importe en USD de las oportunidades abiertas cuya fecha "
            "prevista de cierre cae dentro del periodo seleccionado. Cada "
            "oportunidad se cuenta una vez."
        ),
        "Comerciales",
        (
            "Suma de importes en USD de oportunidades abiertas únicas con "
            "cierre previsto en el periodo."
        ),
    ),
    (
        "Número de oportunidades abiertas",
        "Cantidad de oportunidades abiertas que cumplen los filtros del corte.",
        "Comerciales",
        "Conteo de oportunidades abiertas únicas incluidas en el corte.",
    ),
    (
        "Cuentas con oportunidades abiertas",
        (
            "Cantidad de cuentas distintas con al menos una oportunidad "
            "abierta en el corte."
        ),
        "Comerciales",
        "Conteo de cuentas distintas de las oportunidades abiertas del corte.",
    ),
    (
        "Tarifa de costo estimada en la venta",
        (
            "Tarifa de costo considerada al vender la oportunidad. "
            "Pendiente de validación hasta confirmar fuente, unidad y "
            "asignación."
        ),
        "Comerciales",
        "Pendiente de validación.",
    ),
    (
        "Capacidad del equipo",
        "Horas disponibles del equipo para el periodo consultado.",
        "Operativos",
        (
            "Suma de la capacidad de las personas elegibles durante su "
            "periodo activo: FTE × días laborables × 8 horas."
        ),
    ),
    (
        "Horas registradas",
        (
            "Horas capturadas en Clockify para los proyectos incluidos en "
            "el corte."
        ),
        "Operativos",
        "Suma de horas de registros únicos del periodo, sin Comida.",
    ),
    (
        "Horas facturables",
        "Horas clasificadas como facturables según la regla de Operaciones.",
        "Operativos",
        "Suma de horas que cumplen la regla de facturabilidad del periodo.",
    ),
    (
        "Saldo de capacidad (h)",
        (
            "Capacidad del equipo menos horas registradas. Si el saldo es "
            "negativo, la tarjeta muestra Exceso sobre capacidad."
        ),
        "Operativos",
        "Capacidad del equipo − horas registradas.",
    ),
    (
        "Consumo de capacidad (%)",
        "Horas registradas como porcentaje de la capacidad del equipo.",
        "Operativos",
        "Horas registradas ÷ capacidad del equipo × 100.",
    ),
    (
        "Facturabilidad (%)",
        (
            "Horas facturables como porcentaje de la capacidad del "
            "equipo. Resumen ejecutivo y Operativa usan esta definición e "
            "indican el alcance de cada vista."
        ),
        "Operativos",
        "Horas facturables ÷ capacidad del equipo × 100.",
    ),
    (
        "Horas de inversión operativa",
        "Horas registradas con la etiqueta de inversión operativa.",
        "Operativos",
        "Suma de horas de registros únicos con la etiqueta INV_OPERATIVA.",
    ),
]

SOURCES = {
    "Financieros": "DataRevenue + Clockify + Bandas/rol + Master rates",
    "Comerciales": "Backlog_Proyectos",
    "Operativos": "Clockify + Bandas/rol + cierres publicados",
}
SOURCE_OVERRIDES = {
    "Tarifa de costo estimada en la venta": "Pendiente de validación",
    "Ingresos confirmados futuros": "DataRevenue",
    "Facturación": "DataRevenue",
    "Importe cobrado": "DataRevenue",
    "Porcentaje de cobranza": "DataRevenue",
    "Ingresos contratados": "DataRevenue",
    "Capacidad del equipo": "Bandas/rol + calendario laboral",
}
CONCEPTS = [
    (name, definition, SOURCE_OVERRIDES.get(name, SOURCES[category]))
    for name, definition, category, _ in INDICATORS
]
DEFINITIONS_DATE = "2026-11-17"

GLOSSARY = (
    (
        "Finanzas",
        tuple(
            (name, name, definition)
            for name, definition, category, _ in INDICATORS
            if category == "Financieros"
            and name
            in {"Facturación", "Margen bruto", "Porcentaje de cobranza"}
        ),
    ),
    (
        "Operaciones",
        tuple(
            (name, name, definition)
            for name, definition, category, _ in INDICATORS
            if category == "Operativos"
            and name
            in {
                "Saldo de capacidad (h)",
                "Consumo de capacidad (%)",
                "Facturabilidad (%)",
                "Horas de inversión operativa",
            }
        ),
    ),
    (
        "Comercial",
        tuple(
            (name, name, definition)
            for name, definition, _, _ in INDICATORS
            if name
            in {
                "Ventas ganadas (booking)",
                "Ingresos confirmados futuros",
                "Importe de oportunidades abiertas",
            }
        ),
    ),
)


def indicator_concepts() -> list[dict[str, str]]:
    """Entrega definición y cálculo por separado para el glosario."""
    return [
        {
            "name": name,
            "definition": definition,
            "category": category,
            "calculation": calculation,
            "source": SOURCE_OVERRIDES.get(name, SOURCES[category]),
        }
        for name, definition, category, calculation in INDICATORS
    ]


def glossary_groups() -> list[dict[str, object]]:
    """Agrupa los indicadores de las tres tarjetas ejecutivas."""
    return [
        {
            "name": group,
            "terms": [
                {"term": term, "concept": concept, "summary": summary}
                for term, concept, summary in terms
            ],
        }
        for group, terms in GLOSSARY
    ]
