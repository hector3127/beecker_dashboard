// @ts-check
// DOM presentation; state and reload callbacks belong to the controller.

import { el } from "#app/lib/dom.js";

/** @param {Record<string, any>} ctx Live state and controller callbacks. */
export function renderReference(ctx) {
  const visible = ctx.matched();
  const totalPages = Math.max(1, Math.ceil(visible.length / ctx.size));
  ctx.page = Math.min(ctx.page, totalPages);
  visible.forEach((record) => ctx.table.tBodies[0].append(record.row));
  const shown = new Set(
    visible
      .slice((ctx.page - 1) * ctx.size, ctx.page * ctx.size)
      .map((record) => record.row),
  );
  ctx.records.forEach((record) => {
    record.row.hidden = !shown.has(record.row);
  });
  let empty = ctx.table.querySelector(".eva3-filter-empty");
  if (!visible.length && ctx.rows.length) {
    if (!empty) {
      empty = el(
        "tr",
        { class: "eva3-filter-empty" },
        el("td", {
          colspan: 14,
          class: "vacio",
          text: "No hay proyectos que coincidan con los filtros.",
        }),
      );
      ctx.table.tBodies[0].append(empty);
    }
  } else empty?.remove();
  ctx.count.textContent = `Mostrando ${visible.length ? (ctx.page - 1) * ctx.size + 1 : 0}–${Math.min(ctx.page * ctx.size, visible.length)} de ${visible.length} proyectos`;
  ctx.pagination.replaceChildren(
    el("button", {
      type: "button",
      text: "‹",
      "aria-label": "Página anterior",
      disabled: ctx.page === 1,
      onclick: () => {
        ctx.page--;
        ctx.render();
      },
    }),
    el("span", { class: "eva3-current", text: `${ctx.page} / ${totalPages}` }),
    el("button", {
      type: "button",
      text: "›",
      "aria-label": "Página siguiente",
      disabled: ctx.page === totalPages,
      onclick: () => {
        ctx.page++;
        ctx.render();
      },
    }),
  );
  ctx.tabs
    .querySelectorAll("button")
    .forEach((button) =>
      button.setAttribute(
        "aria-pressed",
        String(button.dataset.service === ctx.tab),
      ),
    );
}
