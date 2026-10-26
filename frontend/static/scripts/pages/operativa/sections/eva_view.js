// @ts-check
// view: operativa/sections/eva. Original data, ordering and interactions are preserved.
import { el, svg } from "#app/lib/dom.js";
import { formatNumber } from "#app/lib/format.js";
import { icon } from "#app/ui/icons.js";
import { NO_VALUE, RESTRICTED, known } from "./eva_model.js";
/**
 * @param {string} name
 */
export function statIcon(name) {
  const paths = {
    folder: "M3 7V4h7l2 3h9v13H3z",
    calendar: "M4 5h16v16H4zM4 10h16M8 2v6m8-6v6M8 14h2m4 0h2m-8 3h2",
    clock: "M12 7v5l4 2",
    active: "M6 8h12v12H6zM9 4h6v4",
    renewal: "M5 6h14v15H5zM8 3v6m8-6v6m-6 6 2 2 4-4",
  };
  return svg(
    "svg",
    {
      viewBox: "0 0 24 24",
      fill: "none",
      stroke: "currentColor",
      "stroke-width": 1.7,
      "aria-hidden": "true",
    },
    ...(name === "clock" ? [svg("circle", { cx: 12, cy: 12, r: 9 })] : []),
    svg("path", { d: paths[name] }),
  );
}
/**
 * @param {string} label
 * @param {any} value
 * @param {string} glyph
 * @param {boolean} negative
 */
export function stat(label, value, glyph, negative = false) {
  return el(
    "div",
    { class: "eva-stat" },
    el(
      "div",
      { class: "eva-label" },
      statIcon(glyph),
      el("span", { text: label }),
    ),
    el("div", {
      class: `eva-value${negative ? " eva-negative" : ""}`,
      text: value,
    }),
  );
}
/**
 * @param {string} href
 * @param {string} text
 */
export const more = (href, text) =>
  el("a", { class: "eva-more", href }, `${text} →`);
/**
 * @param {string} title
 * @param {string} subtitle
 * @param {string} href
 * @param {string} label
 */
export function header(title, subtitle, href, label) {
  return el(
    "div",
    { class: "eva-head" },
    el("span", { class: "eva-icon" }, icon("people", 26)),
    el(
      "div",
      { class: "eva-title" },
      el("strong", { text: title }),
      el("small", { text: subtitle }),
    ),
    el("a", { class: "eva-go", href, "aria-label": label }, icon("arrow", 20)),
  );
}
/**
 * @param {any} options
 */
export function timeCostCard({
  title,
  subtitle,
  href,
  ariaLabel,
  daysLabel,
  moreText,
  card,
  tone,
}) {
  const head = header(title, subtitle, href, ariaLabel);
  if (card === null)
    return el(
      "div",
      { class: `eva-card ${tone}` },
      head,
      el("p", { class: "ops-muted eva-restricted", text: RESTRICTED }),
    );
  const shown = card.available;
  return el(
    "div",
    { class: `eva-card ${tone}` },
    head,
    el(
      "div",
      { class: "eva-stats" },
      stat("Proyectos (TP)", shown ? card.total_projects : NO_VALUE, "folder"),
      stat(
        daysLabel,
        shown && known(card.time_days)
          ? `${formatNumber(card.time_days, 1)} d`
          : NO_VALUE,
        "calendar",
        shown && card.time_days < 0,
      ),
      stat(
        "Avance en horas",
        shown && known(card.cost_percent)
          ? `${formatNumber(card.cost_percent, 0)}%`
          : NO_VALUE,
        "clock",
      ),
    ),
    more(href, moreText),
  );
}
/**
 * @param {HTMLElement} root
 * @param {any} view
 * @param {any} urls
 */
export function renderEva(root, view, urls) {
  const { eva1, eva3, eva4 } = view.eva;
  root.replaceChildren(
    timeCostCard({
      title: "EVA 1",
      subtitle: "IXB y RaaS",
      href: urls.eva1,
      ariaLabel: "Ver detalle de EVA 1",
      daysLabel: "Desviación (días)",
      moreText: "Ver proyectos",
      card: eva1,
      tone: "eva-tone-violet",
    }),
    timeCostCard({
      title: "EVA 3",
      subtitle: "AER y T&M",
      href: urls.eva3,
      ariaLabel: "Ver detalle de EVA 3",
      daysLabel: "Días para renovar",
      moreText: "Ver proyectos",
      card: eva3,
      tone: "eva-tone-blue",
    }),
    el(
      "div",
      { class: "eva-card eva-tone-orange", id: "ops-eva4-card" },
      header(
        "EVA 4",
        "Servicios de ROC",
        urls.eva4,
        "Ver detalle de EVA-04 Report",
      ),
      el(
        "div",
        { class: "eva-stats eva-stats-two" },
        stat("Activos", eva4.available ? eva4.active : NO_VALUE, "active"),
        stat(
          "Por renovar",
          eva4.available ? eva4.renewal_count : NO_VALUE,
          "renewal",
        ),
      ),
      more(urls.eva4, "Ver proyectos"),
    ),
  );
}
