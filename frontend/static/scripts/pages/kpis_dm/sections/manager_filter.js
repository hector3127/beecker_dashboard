// @ts-check
import { el, svg } from "#app/lib/dom.js";

/** @param {any} filters Global selection submitted with the cut form. */
export function managerFilter(filters) {
  const selected = new Set(filters.selected_managers);
  const all = selected.size === 0;
  const count = el("span", { class: "kpi-dm-count" });
  const trigger = el("summary", {},
    el("span", { text: "Delivery Managers" }), count,
    svg("svg", { viewBox: "0 0 24 24", "aria-hidden": "true" },
      svg("path", { d: "m7 10 5 5 5-5", fill: "none", stroke: "currentColor", "stroke-width": 2 })),
  );
  const chooser = el("details", { class: "kpi-dm-chooser", id: "kpi-global-dms" }, trigger);
  const status = el("span", { class: "kpi-dm-status", role: "status" });
  const list = el("div", { class: "kpi-dm-list" });
  const empty = el("p", { class: "kpi-dm-empty", text: "No hay DMs con ese nombre.", hidden: true });
  const normalize = (/** @type {string} */ value) => value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim();
  const rows = filters.managers.map((/** @type {string} */ name) => {
    const input = /** @type {HTMLInputElement} */ (el("input", { type: "checkbox", name: "dm", value: name, checked: all || selected.has(name) }));
    const label = el("label", { class: "kpi-dm-row" }, input, el("span", { text: name }));
    list.append(label);
    return { input, label, search: normalize(name) };
  });
  function update() {
    const n = rows.filter((row) => row.input.checked).length;
    count.textContent = n === rows.length ? "Todos" : `${n} seleccionados`;
    status.textContent = `${n} de ${rows.length} seleccionados`;
  }
  for (const row of rows) row.input.addEventListener("change", update);
  const search = el("input", {
    type: "search", class: "kpi-dm-search", placeholder: "Buscar DM…", "aria-label": "Buscar Delivery Manager",
    oninput: (/** @type {any} */ event) => {
      const query = normalize(event.target.value);
      for (const row of rows) row.label.hidden = !row.search.includes(query);
      empty.hidden = rows.some((row) => !row.label.hidden);
    },
    onkeydown: (/** @type {KeyboardEvent} */ event) => { if (event.key === "Enter") event.preventDefault(); },
  });
  const actions = el("div", { class: "kpi-dm-actions" },
    ...[["Todos", true], ["Ninguno", false]].map(([label, checked]) => el("button", {
      type: "button", text: label,
      onclick: () => { for (const row of rows) row.input.checked = Boolean(checked); update(); },
    })),
  );
  const panel = el("div", { class: "kpi-dm-panel", role: "group", "aria-label": "Selección global de Delivery Managers" },
    el("div", { class: "kpi-dm-heading" }, el("strong", { text: "Filtrar por DM" }), el("span", { text: "Aplica a todas las tablas y la tendencia" })),
    search, actions, list, empty,
    el("div", { class: "kpi-dm-footer" }, status, el("button", { type: "submit", text: "Aplicar DMs" })),
  );
  chooser.append(panel);
  chooser.addEventListener("toggle", () => {
    if (!chooser.hasAttribute("open")) return;
    const rect = chooser.getBoundingClientRect();
    const below = window.innerHeight - rect.bottom - 16;
    const above = rect.top - 16;
    const up = below < 300 && above > below;
    chooser.classList.toggle("kpi-dm-up", up);
    panel.style.maxHeight = `${Math.max(240, Math.min(480, (up ? above : below) - 8))}px`;
  });
  chooser.addEventListener("keydown", (event) => {
    if (event.key === "Escape") { chooser.removeAttribute("open"); trigger.focus(); }
  });
  const outside = (/** @type {PointerEvent} */ event) => {
    if (!chooser.isConnected) { document.removeEventListener("pointerdown", outside); return; }
    if (!chooser.contains(/** @type {Node} */ (event.target))) chooser.removeAttribute("open");
  };
  document.addEventListener("pointerdown", outside);
  update();
  return chooser;
}
