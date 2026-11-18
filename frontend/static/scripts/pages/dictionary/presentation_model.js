// @ts-check
export const CATEGORIES = ["Financieros", "Comerciales", "Operativos"];

/** @param {{name: string, definition: string, category?: string, calculation?: string}} concept */
export function presentation(concept) {
  const category = CATEGORIES.includes(concept.category || "") ? concept.category : CATEGORIES[0];
  return {
    category,
    icon: category === "Operativos" ? "clock" : category === "Comerciales" ? "chart" : "coins",
    tone: category === "Operativos" ? "blue" : category === "Comerciales" ? "pink" : "purple",
    formula: concept.calculation || "Pendiente de validación.",
    definition: concept.definition,
  };
}
