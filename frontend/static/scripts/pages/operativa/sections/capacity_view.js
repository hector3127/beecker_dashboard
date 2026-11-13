import { apiGet } from '#app/data/api-client.js';

function openMonthlyDetail(month) {
  const body = el('div', {class: 'ops-month-detail-body', text: 'Cargando registros…'});
  const close = el('button', {type: 'button', class: 'ops-button', text: 'Cerrar'});
  const dialog = el('dialog', {class: 'ops-month-detail', 'aria-label': 'Detalle mensual de horas'},
    el('header', {}, el('h2', {text: 'Detalle de horas · ' + month}), close), body);
  const controller = new AbortController();
  close.addEventListener('click', () => dialog.close());
  dialog.addEventListener('close', () => { controller.abort(); dialog.remove(); });
  document.body.append(dialog);
  dialog.showModal();
  apiGet('screens/capacidad/diaria/', {mes: month}, {signal: controller.signal}).then(({data}) => {
    if (!data.ok) throw new Error(data.error);
    const search = el('input', {type: 'search', placeholder: 'Buscar persona, proyecto o servicio', 'aria-label': 'Buscar en el detalle'});
    const rows = (data.detalleMensual ?? []).map(row => el('tr', {},
      ...[row.persona, row.proyecto || 'Sin proyecto', row.servicio,
        row.facturable ? 'Facturable' : 'No facturable', formatNumber(row.horas, 2) + ' h']
        .map(text => el('td', {text}))));
    const empty = el('p', {text: 'Sin registros para esta consulta.'});
    const filter = () => {
      const query = search.value.trim().toLocaleLowerCase();
      for (const row of rows) row.hidden = !row.textContent.toLocaleLowerCase().includes(query);
      empty.hidden = rows.some(row => !row.hidden);
    };
    search.addEventListener('input', filter);
    body.replaceChildren(search, el('table', {},
      el('thead', {}, el('tr', {}, ...['Persona', 'Proyecto', 'Servicio', 'Tipo de hora', 'Horas']
        .map(text => el('th', {scope: 'col', text})))),
      el('tbody', {}, ...rows)), empty);
    filter();
  }).catch(error => { if (!controller.signal.aborted) body.textContent = error.message; });
}

// @ts-check
// view: operativa/sections/capacity. Original data, ordering and interactions are preserved.
import { el } from "#app/lib/dom.js";
import { formatNumber } from "#app/lib/format.js";
import { icon } from "#app/ui/icons.js";
import {
  NO_VALUE,
  RESTRICTED,
  known,
  hours,
  meterPercent,
  ratio,
} from "./capacity_model.js";
/**
 * @param {string} label
 * @param {any} value
 * @param {string} note
 * @param {any} tone
 */
export function stat(label, value, note, tone) {
  return el(
    "div",
    { class: `capacity-stat ${tone}` },
    el("span", { class: "capacity-stat-label", text: label }),
    el("strong", { text: hours(value) }),
    el("small", { text: note }),
  );
}
/**
 * @param {string} label
 * @param {any} value
 * @param {string} note
 * @param {string} glyph
 */
export function detail(label, value, note, glyph) {
  return el(
    "div",
    { class: "capacity-detail-row" },
    el("span", { class: "capacity-detail-icon" }, icon(glyph, 20)),
    el("span", { text: label }),
    el(
      "div",
      {},
      el("strong", { text: hours(value) }),
      el("small", { text: note }),
    ),
  );
}
/**
 * @param {HTMLElement} root
 * @param {Record<string, any>|null} capacity
 */
export function renderCapacity(root, capacity) {
  const section = root.closest(".ops-capacity-section");
  const details = section?.querySelector("#ops-capacity-details");
  const period = section?.querySelector("#ops-capacity-month");
  details?.replaceChildren();
  if (capacity === null) {
    root.replaceChildren(
      el("p", { class: "ops-muted capacity-message", text: RESTRICTED }),
    );
    if (period) period.textContent = "Acceso limitado";
    return;
  }
  if (/^\d{4}-\d{2}$/.test(capacity.month || '')) {
    const button = el('button', {type: 'button', class: 'ops-button', text: 'Ver horas por persona'});
    button.addEventListener('click', () => openMonthlyDetail(capacity.month));
    details?.append(button);
  }
  if (period) {
    const valid = /^\d{4}-\d{2}$/.test(capacity.month || "");
    const date = valid
      ? new Date(
          Number(capacity.month.slice(0, 4)),
          Number(capacity.month.slice(5, 7)) - 1,
          1,
        )
      : null;
    const text = date
      ? date.toLocaleDateString("es-MX", { month: "long", year: "numeric" })
      : "Periodo pendiente";
    period.textContent = text[0].toUpperCase() + text.slice(1);
  }
  section?.classList.toggle("capacity-clockify", capacity.source === "clockify");
  const available = !capacity.error && known(capacity.available);
  const left = el(
    "div",
    { class: "capacity-main" },
    el(
      "div",
      { class: "capacity-main-heading" },
      el("span", { class: "capacity-main-icon" }, icon("team", 25)),
      el("h3", { text: "Saldo de capacidad" }),
      el("span", {
        class: "capacity-info",
        title:
          "Capacidad base del mes menos las horas registradas en Clockify.",
        text: "ⓘ",
      }),
    ),
    el("strong", {
      class: "capacity-main-value",
      text: available ? formatNumber(capacity.available, 0) : NO_VALUE,
    }),
    el("p", {
      class: "capacity-main-caption",
      text: capacity.loading ? "Calculando…" : capacity.error ? "Datos no disponibles" : "horas disponibles",
    }),
    el("p", {
      class: "capacity-main-period",
      text: capacity.loading
        ? ""
        : `${capacity.month || "Periodo pendiente"} · ${capacity.people ?? "—"} personas vigentes · ${capacity.registered_people ?? "—"} con horas`,
    }),
  );
  if (capacity.loading || capacity.error) {
    root.replaceChildren(
      left,
      el("p", {
        class: "ops-muted capacity-message",
        text: capacity.loading
          ? "Calculando capacidad y horas registradas…"
          : capacity.error,
      }),
    );
    return;
  }
  const usageKnown =
    known(capacity.consumed) && known(capacity.base) && capacity.base > 0;
  const percent = usageKnown
    ? meterPercent(capacity.consumed, capacity.base)
    : 0;
  const actualPercent = usageKnown ? Math.round(capacity.consumed / capacity.base * 100) : 0;
  const meter = el(
    "div",
    {
      class: "ops-meter",
      role: "img",
      "aria-label": usageKnown
        ? `Horas registradas respecto a capacidad base: ${actualPercent}%`
        : "Uso de capacidad pendiente",
    },
    el("i"),
  );
  meter.firstElementChild.style.width = `${Math.min(100, actualPercent)}%`;
  const baseText =
    `Capacidad base del mes: ${hours(capacity.base, 0)} (suma de horas disponibles por persona). ${capacity.over ?? "—"} personas sobre jornada.`;
  const center = el(
    "div",
    { class: "capacity-usage" },
    el(
      "h3",
      {},
      "Uso de la capacidad del equipo ",
      el("span", {
        class: "capacity-info",
        title:
          "Horas registradas en Clockify divididas entre la capacidad base del mes. El medidor se limita a 0–100%.",
        text: "ⓘ",
      }),
    ),
    el(
      "div",
      { class: "capacity-meter-row" },
      meter,
      el(
        "div",
        { class: "capacity-meter-value" },
        el("strong", { text: usageKnown ? `${actualPercent}%` : NO_VALUE }),
        el("span", { text: "utilizado" }),
      ),
    ),
    el(
      "div",
      { class: "capacity-stats" },
      stat(
        "Horas facturables",
        capacity.billable,
        ratio(capacity.billable, capacity.base),
        "capacity-stat-billable",
      ),
      stat(
        "Horas disponibles",
        capacity.available,
        ratio(capacity.available, capacity.base),
        "capacity-stat-available",
      ),
      stat(
        "Horas registradas",
        capacity.consumed,
        "Facturables y no facturables",
        "capacity-stat-estimated",
      ),
    ),
    el(
      "div",
      { class: "capacity-notes" },
      el("span", { "aria-hidden": "true", text: "ⓘ" }),
      el(
        "div",
        {},
        el("p", {
          text: capacity.refresh_error
            ? `Último resultado disponible. No se pudo actualizar: ${capacity.refresh_error}`
            : "Horas reales de Clockify de las personas con banda vigente en el mes, facturables o no y sin Comida.",
        }),
        el("p", { text: baseText }),
      ),
    ),
  );
  details?.replaceChildren(
    detail(
      "Consumo actual (Clockify)",
      capacity.consumed,
      capacity.clockify_month ? `${formatNumber(capacity.clockify_month.entries)} registros · ${capacity.clockify_month.people} personas con horas` : ratio(capacity.consumed, capacity.base),
      "pause",
    ),
    detail(
      "Horas facturables",
      capacity.billable,
      ratio(capacity.billable, capacity.base),
      "chart",
    ),
    detail(
      "Capacidad base del mes",
      capacity.base,
      "Suma de la capacidad del mes por persona",
      "target",
    ),
  );
  root.replaceChildren(left, center);
}
