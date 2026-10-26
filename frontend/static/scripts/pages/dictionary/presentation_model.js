// @ts-check
// model: dictionary/presentation. Original data, ordering and interactions are preserved.
export const CATEGORIES = [
  "Ventas y revenue",
  "Facturación y cobranza",
  "Costos y márgenes",
  "Proyectos y operación",
  "Recursos",
  "Finanzas",
  "Comparaciones",
  "Otros",
];
/** @type {Record<string, [number, string, string, string]>} */
export const PRESENTATION = {
  Periodo: [7, "calendar", "purple", "Desde ≤ fecha ≤ Hasta"],
  Importes: [5, "coins", "green", "1,897,644.14 → 1.89M"],
  Facturación: [
    1,
    "file",
    "pink",
    "Invoiced + Invoiced Factoring + Collected + Collected Factoring",
  ],
  "Revenue contratado": [
    0,
    "card",
    "purple",
    "Confirmed + estados facturados y cobrados",
  ],
  "Booking / ventas cerradas": [
    0,
    "chart",
    "green",
    "Σ oportunidades ganadas del rango (USD)",
  ],
  Cobranza: [
    1,
    "money",
    "pink",
    "100 × Collected ÷ (Invoiced + Collected), incluido Factoring",
  ],
  Costos: [2, "coins", "blue", "Σ horas únicas × tarifa interna de banda"],
  "Utilidad bruta": [
    2,
    "chart",
    "purple",
    "Facturación del periodo − costos del periodo",
  ],
  "Margen bruto": [2, "percent", "green", "100 × utilidad bruta ÷ facturación"],
  "Rentabilidad mensual": [
    5,
    "calendar",
    "pink",
    "Facturación mensual y costos del mes",
  ],
  "Comparación de cuentas": [
    6,
    "balance",
    "amber",
    "Facturación, utilidad bruta o margen bruto",
  ],
  "Tarifa de costo vendida (costing rate)": [2, "tag", "purple", ""],
  "Tarifa interna de banda": [
    4,
    "layers",
    "blue",
    "Tarifa por hora de la banda del recurso",
  ],
  ETC: [3, "clock", "purple", "Presupuesto de horas − horas consumidas"],
  "FTE equivalente": [
    4,
    "calendar",
    "purple",
    "ETC ÷ meses calendario del rango ÷ 360",
  ],
  "Avance en horas": [3, "chart", "pink", "100 × consumo ÷ presupuesto"],
  "Facturabilidad global": [
    4,
    "chart",
    "purple",
    "100 × horas facturables ÷ capacidad",
  ],
  "Inversión operativa": [
    3,
    "chart",
    "green",
    "Σ horas únicas con etiqueta INV_OPERATIVA",
  ],
  "Trabajo por entregar": [
    0,
    "clock",
    "purple",
    "Σ Confirmed con fecha G futura dentro del rango",
  ],
  "Previas al cierre": [
    0,
    "flag",
    "pink",
    "Σ oportunidades abiertas únicas del periodo (USD)",
  ],
  "Decisiones y seguimiento": [7, "file", "green", ""],
  "Corte fijo": [7, "layers", "purple", "Corte preparado por rango"],
  "Margen vendido vs. real por oportunidad": [
    6,
    "target",
    "orange",
    "Real = 100 × (revenue − costos disponibles) ÷ revenue",
  ],
};
/**
 * @param {{name: string, definition: string}} concept
 */
export function presentation(concept) {
  const [index, icon, tone, formula] = PRESENTATION[concept.name] || [
    7,
    "file",
    "purple",
    "",
  ];
  // Separar notas sin resumir ni eliminar texto de la fuente.
  const parts = concept.definition.split(/(?<=[.!?])\s+/);
  const lead = concept.name === "Importes" ? 2 : 1;
  return {
    category: CATEGORIES[index],
    icon,
    tone,
    formula,
    definition: parts.slice(0, lead).join(" "),
    notes: parts.slice(lead).join(" "),
  };
}
