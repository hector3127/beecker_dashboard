// @ts-check
// Metadatos visuales; las definiciones originales siguen viniendo de la API.
import { svg } from '#app/lib/dom.js';

export const CATEGORIES = ['Ventas y revenue', 'Facturación y cobranza', 'Costos y márgenes', 'Proyectos y operación', 'Recursos', 'Finanzas', 'Comparaciones', 'Otros'];
const PRESENTATION = {
  'Periodo': [7, 'calendar', 'purple', 'Desde ≤ fecha ≤ Hasta'],
  'Importes': [5, 'coins', 'green', '1,897,644.14 → 1.89M'],
  'Facturación': [1, 'file', 'pink', 'Invoiced + Invoiced Factoring + Collected + Collected Factoring'],
  'Revenue contratado': [0, 'card', 'purple', 'Confirmed + estados facturados y cobrados'],
  'Booking / ventas cerradas': [0, 'chart', 'green', 'Σ oportunidades ganadas del rango (USD)'],
  'Cobranza': [1, 'money', 'pink', '100 × Collected ÷ (Invoiced + Collected), incluido Factoring'],
  'Costos': [2, 'coins', 'blue', 'Σ horas únicas × tarifa interna de banda'],
  'Utilidad bruta': [2, 'chart', 'purple', 'Facturación del periodo − costos del periodo'],
  'Margen bruto': [2, 'percent', 'green', '100 × utilidad bruta ÷ facturación'],
  'Rentabilidad mensual': [5, 'calendar', 'pink', 'Facturación mensual y costos del mes'],
  'Comparación de cuentas': [6, 'balance', 'amber', 'Facturación, utilidad bruta o margen bruto'],
  'Tarifa de costo vendida (costing rate)': [2, 'tag', 'purple', ''],
  'Tarifa interna de banda': [4, 'layers', 'blue', 'Tarifa por hora de la banda del recurso'],
  'ETC': [3, 'clock', 'purple', 'Presupuesto de horas − horas consumidas'],
  'FTE equivalente': [4, 'calendar', 'purple', 'ETC ÷ meses calendario del rango ÷ 360'],
  'Avance en horas': [3, 'chart', 'pink', '100 × consumo ÷ presupuesto'],
  'Facturabilidad global': [4, 'chart', 'purple', '100 × horas facturables ÷ capacidad'],
  'Inversión operativa': [3, 'chart', 'green', 'Σ horas únicas con etiqueta INV_OPERATIVA'],
  'Trabajo por entregar': [0, 'clock', 'purple', 'Σ Confirmed con fecha G futura dentro del rango'],
  'Previas al cierre': [0, 'flag', 'pink', 'Σ oportunidades abiertas únicas del periodo (USD)'],
  'Decisiones y seguimiento': [7, 'file', 'green', ''],
  'Corte fijo': [7, 'layers', 'purple', 'Corte preparado por rango'],
  'Margen vendido vs. real por oportunidad': [6, 'target', 'orange', 'Real = 100 × (revenue − costos disponibles) ÷ revenue'],
};

/** @param {{name:string, definition:string}} concept */
export function presentation(concept) {
  const [index, icon, tone, formula] = PRESENTATION[concept.name] || [7, 'file', 'purple', ''];
  // Separar notas sin resumir ni eliminar texto de la fuente.
  const parts = concept.definition.split(/(?<=[.!?])\s+/);
  const lead = concept.name === 'Importes' ? 2 : 1;
  return { category: CATEGORIES[index], icon, tone, formula,
    definition: parts.slice(0, lead).join(' '), notes: parts.slice(lead).join(' ') };
}

const PATHS = {
  calendar: ['M4 5h16v16H4zM4 10h16M8 3v4M16 3v4M8 14h2M14 14h2M8 18h2'],
  coins: ['M4 6c0 4 16 4 16 0S4 2 4 6ZM4 6v12c0 4 16 4 16 0V6M4 12c0 4 16 4 16 0'],
  file: ['M6 3h8l4 4v14H6V3ZM14 3v5h4M9 12h6M9 16h6'],
  card: ['M3 5h18v14H3zM3 10h18M6 15h5'],
  chart: ['M4 20v-7h3v7ZM10 20V8h3v12ZM16 20V3h3v17Z'],
  money: ['M12 5v14M16 8c-6-4-10 3-4 4s4 7-4 4', 'M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0'],
  percent: ['M6 18 18 6M8 6a2 2 0 1 0-4 0 2 2 0 0 0 4 0M20 18a2 2 0 1 0-4 0 2 2 0 0 0 4 0'],
  balance: ['M12 3v18M6 21h12M4 7h16M6 7l-4 8h8L6 7ZM18 7l-4 8h8l-4-8Z'],
  tag: ['M3 3h9l9 9-9 9-9-9V3ZM7 7h1'],
  layers: ['m3 7 9-5 9 5-9 5-9-5ZM3 12l9 5 9-5M3 17l9 5 9-5'],
  clock: ['M12 6v6h5', 'M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0'],
  flag: ['M5 22V3l14 1v9L5 12'],
  target: ['M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0', 'M18 12a6 6 0 1 1-12 0 6 6 0 0 1 12 0', 'M14 12a2 2 0 1 1-4 0 2 2 0 0 1 4 0'],
};
/** @param {string} name */
export function dictionaryIcon(name) {
  return svg('svg', { viewBox:'0 0 24 24', fill:'none', stroke:'currentColor',
    'stroke-width':'1.8', 'stroke-linecap':'round', 'stroke-linejoin':'round', 'aria-hidden':'true' },
  ...(PATHS[name] || PATHS.file).map(d => svg('path', {d})));
}
