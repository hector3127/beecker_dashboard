// @ts-check
// Pestañas, filtro de periodo, indicadores y tabla por Delivery Manager.
import { el } from "#app/lib/dom.js";
import { formatNumber } from "#app/lib/format.js";
import { createPeriodPicker } from "#app/ui/period-picker.js";

export const DASH = "—";
/** Dias con un decimal: 4.5 d. @param {number | null} value */
export const days = (value) =>
  value === null ? DASH : `${formatNumber(value, 1)} d`;
/** Porcentaje con un decimal. @param {number | null} value */
export const percent = (value) =>
  value === null ? DASH : `${formatNumber(value, 1)}%`;
/** @param {number} n @param {string} one @param {string} many */
const plural = (n, one, many) => (n === 1 ? one : many);
/** Color segun la proporcion en tiempo. @param {number} value */
const tone = (value) => (value < 40 ? " lo" : value >= 80 ? " hi" : "");

/** @param {Record<string, string>} urls @param {string} query */
export function renderTabs(urls, query) {
  const tab = (
    /** @type {string} */ href,
    /** @type {string} */ text,
    /** @type {boolean} */ on = false,
  ) => el("a", { class: on ? "on" : null, href: href + query, text });
  return el(
    "div",
    { class: "tabs" },
    tab(urls.facturabilidad, "Facturabilidad"),
    tab(urls.especialidad, "Facturabilidad por especialidad"),
    tab(urls.recurso, "Facturabilidad por recurso"),
    tab(urls.kpis, "KPIs de Delivery Managers", true),
    tab(urls.area, "Facturabilidad por área"),
  );
}

/** @param {any} data */
export function renderFilter(data) {
  const { picker, cut } = data;
  const hint = cut.current
    ? `Corte actual (${cut.label}).`
    : `Corte al ${cut.label}, reconstruido con las horas de Clockify hasta esa fecha.`;
  const form = el(
    "form",
    {
      method: "get",
      style: {
        display: "flex",
        flexWrap: "wrap",
        alignItems: "center",
        gap: "10px 14px",
        margin: "0 0 14px",
        fontSize: "14px",
        color: "#3A3870",
      },
    },
    createPeriodPicker(picker),
    el("span", {
      class: "hint",
      text: `${hint} Los meses se reconstruyen por fecha; los trimestres promedian los cortes mensuales.`,
    }),
  );
  const note = el(
    "details",
    { class: "kpi-definition-note" },
    el("summary", { text: "Cómo interpretar TP, T y C en esta pantalla" }),
    el("p", {
      text: "Base: proyectos abiertos de EVA 1, incluidos suspendidos. Corte al último lunes a jueves de cada mes; viernes, sábado y domingo retroceden al jueves. TP: proyectos del DM. T: proyectos con desviación ≤ 0 / TP × 100. C: proyectos con avance ≤ 100% / TP × 100. Cero días y exactamente 100% cumplen. Si falta un dato, su porcentaje queda pendiente y TP se conserva. El mes actual es provisional hasta el último lunes–jueves disponible.",
    }),
  );
  return [form, note];
}

/** @param {string} label @param {Node | string} value @param {string} note @param {string} [valueClass] */
function card(label, value, note, valueClass = "kv") {
  return el(
    "div",
    { class: "kc" },
    el("div", { class: "kl", text: label }),
    el("div", { class: valueClass }, value),
    el("div", { class: "ke", text: note }),
  );
}

/** @param {any} summary */
export function renderCards(summary) {
  const { totals, best, worst } = summary;
  /** @param {any} row */
  const share = (row) =>
    row
      ? `${percent(row.t)} en tiempo, ${row.total} proyecto${plural(row.total, "", "s")}`
      : "";
  return el(
    "section",
    { class: "kp" },
    card(
      "Cumplimiento en costo (C)",
      percent(totals.c),
      `Proyectos dentro del presupuesto · T: ${percent(totals.t)}`,
    ),
    card(
      "Carga total (TP)",
      String(totals.total),
      `${percent(totals.t)} en tiempo`,
    ),
    card(
      "Mayor proporción en tiempo",
      best ? best.name : DASH,
      share(best),
      "kv txt",
    ),
    card(
      "Menor proporción en tiempo",
      worst ? worst.name : DASH,
      share(worst),
      "kv txt",
    ),
  );
}

/** @param {any} summary @param {string} managerUrl */
export function renderTable(summary, managerUrl) {
  const { rows, totals } = summary;
  const num = (/** @type {string} */ text, /** @type {string} */ extra = "") =>
    el("td", { class: `num${extra}`, text });
  const body = rows.length
    ? rows.map((/** @type {any} */ r) =>
        el(
          "tr",
          {},
          el(
            "td",
            {},
            el(
              "b",
              {},
              el("a", {
                href: managerUrl.replace(
                  "slug-placeholder",
                  encodeURIComponent(r.slug),
                ),
                text: r.name,
              }),
            ),
          ),
          el("td", { class: "g num", text: r.total }),
          num(percent(r.t)),
          num(percent(r.c)),
          num(percent(r.t), r.t === null ? "" : tone(r.t)),
          num(String(r.time_late ?? r.at_risk)),
          num(String(r.cost_over ?? r.critical)),
        ),
      )
    : [
        el(
          "tr",
          {},
          el("td", {
            colspan: 7,
            class: "na",
            text: "Sin proyectos en ejecución.",
          }),
        ),
      ];
  return el(
    "div",
    { class: "card" },
    el("h2", { text: "Por Delivery Manager" }),
    el("div", {
      class: "hs",
      text: "TP: proyectos abiertos al corte de EVA 1. T: % con desviación ≤ 0. C: % con avance ≤ 100%. Fuera de tiempo y fuera de costo son conteos independientes; un proyecto puede aparecer en ambos.",
    }),
    el(
      "div",
      { class: "table-scroll" },
      el(
        "table",
        {},
        el(
          "thead",
          {},
          el(
            "tr",
            {},
            ...[
              "DM",
              "TP",
              "T",
              "C",
              "En tiempo",
              "Fuera de tiempo",
              "Fuera de costo",
            ].map((text) => el("th", { text })),
          ),
        ),
        el("tbody", {}, ...body),
        el(
          "tfoot",
          {},
          el(
            "tr",
            {},
            el("td", { text: "Total" }),
            el("td", { class: "g num", text: totals.total }),
            num(percent(totals.t)),
            num(percent(totals.c)),
            num(percent(totals.t), totals.t === null ? "" : tone(totals.t)),
            num(String(totals.time_late ?? totals.at_risk)),
            num(String(totals.cost_over ?? totals.critical)),
          ),
        ),
      ),
    ),
    el("p", {
      class: "note",
      text: "En tiempo: rojo menos de 40%, verde 80% o más.",
    }),
  );
}
