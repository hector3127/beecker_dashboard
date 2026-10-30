// @ts-check
// Glosario de indicadores de KPIs DM, con la presentación del de Business Overview.
import { el, svg } from "#app/lib/dom.js";

const ICONS = {
  load: [["path", { d: "M4 20v-7h3v7ZM10 20V8h3v12ZM16 20V3h3v17Z" }]],
  clock: [["circle", { cx: 12, cy: 12, r: 10 }], ["path", { d: "M12 6v6l5 3" }]],
  check: [["circle", { cx: 12, cy: 12, r: 10 }], ["path", { d: "m8 12 3 3 5-6" }]],
  alert: [["path", { d: "M12 3 2 21h20L12 3Z" }], ["path", { d: "M12 10v5M12 18v1" }]],
  calendar: [["rect", { x: 4, y: 5, width: 16, height: 16, rx: 2 }], ["path", { d: "M8 3v4m8-4v4M4 10h16" }]],
  info: [["circle", { cx: 12, cy: 12, r: 10 }], ["path", { d: "M12 11v6M12 7v1" }]],
  book: [["path", { d: "M12 5c-3-3-8-3-10-2v16c2-1 7-1 10 2 3-3 8-3 10-2V3c-2-1-7-1-10 2ZM12 5v16" }]],
};

/** @param {keyof typeof ICONS} name */
const icon = (name) =>
  svg("svg", { viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", "stroke-width": 1.8, "stroke-linecap": "round", "stroke-linejoin": "round", "aria-hidden": "true" },
    ...ICONS[name].map(([tag, attrs]) => svg(/** @type {string} */ (tag), /** @type {any} */ (attrs))));

/** @type {{ name: string, note: string, icon: keyof typeof ICONS, terms: [string, string, keyof typeof ICONS][] }[]} */
const GROUPS = [
  {
    name: "Carga y tiempo",
    note: "Qué proyectos se cuentan y cuántos van en tiempo.",
    icon: "load",
    terms: [
      ["TP · carga total", "Proyectos guardados del Delivery Manager en la captura, incluidos los suspendidos. Los pendientes permanecen en TP.", "load"],
      ["T · en tiempo", "T: proyectos con desviación ≤ 0 / TP × 100. Cero días de desviación cuenta como en tiempo.", "clock"],
      ["Fuera de tiempo", "Conteo de proyectos con desviación mayor a cero. Es independiente de fuera de costo.", "alert"],
    ],
  },
  {
    name: "Costo",
    note: "Cumplimiento del presupuesto de horas.",
    icon: "check",
    terms: [
      ["C · cumplimiento en costo", "C: proyectos con avance ≤ 100% / TP × 100. Exactamente 100% cuenta como cumplimiento; más alto es mejor.", "check"],
      ["Fuera de costo", "Conteo de proyectos con avance mayor a 100%. Un proyecto puede estar fuera de tiempo y de costo a la vez.", "alert"],
      ["Datos pendientes", "Un guion (—) indica que no hay información suficiente; no equivale a cero y no suma al numerador.", "info"],
    ],
  },
  {
    name: "Periodos",
    note: "Cómo se eligen los cortes y los promedios.",
    icon: "calendar",
    terms: [
      ["Corte mensual", "Cada mes usa su captura del último lunes a jueves; viernes, sábado y domingo retroceden al jueves.", "calendar"],
      ["Histórico por trimestre", "Promedio de los meses del trimestre, como AVERAGE en Excel. TP es la carga promedio mensual redondeada.", "load"],
      ["Mes abierto (*)", "El mes en curso es provisional. Los meses futuros no tienen datos y los años se eligen en el filtro superior.", "info"],
    ],
  },
];

/** @returns {HTMLElement} */
export function renderGlossary() {
  const groups = GROUPS.map((group, index) =>
    el("section", { class: `kpi-gl-group kpi-gl-group-${index + 1}` },
      el("div", { class: "kpi-gl-heading" },
        el("span", { class: "kpi-gl-icon" }, icon(group.icon)),
        el("div", {}, el("h3", { text: group.name }), el("p", { text: group.note }))),
      el("dl", {}, ...group.terms.map(([term, text, name], position) =>
        el("div", { class: "kpi-gl-term" },
          el("dt", {}, el("span", { class: `kpi-gl-icon kpi-gl-icon-${position + 1}` }, icon(name)), term),
          el("dd", { text }))))));
  return el("details", { class: "kpi-glossary kpi-definition-note" },
    el("summary", {},
      el("span", { class: "kpi-gl-question", "aria-hidden": "true", text: "?" }),
      el("span", { class: "kpi-gl-title" },
        el("strong", { text: "¿Qué significa cada indicador?" }),
        el("span", { text: "TP, T y C: qué cuenta cada uno y cómo se calcula en esta vista." })),
      el("span", { class: "kpi-gl-hint" }, icon("book"), " Consultar glosario")),
    el("div", { class: "kpi-gl-grid" }, ...groups),
    el("p", { class: "kpi-gl-foot", text: "Las cifras se leen de tablas propias de KPIs, sin recalcular desde EVA, Azure ni Clockify. La programación diaria y el cierre mensual se activarán en Genesis." }));
}
