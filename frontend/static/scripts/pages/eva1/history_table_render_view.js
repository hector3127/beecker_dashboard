// @ts-check
// DOM presentation; state and reload callbacks belong to the controller.

import { el } from "#app/lib/dom.js";

/** @param {Record<string, any>} ctx Live state and controller callbacks. */
export function renderReference(ctx) {
  const filtered = ctx.results(),
    totalPages = Math.max(1, Math.ceil(filtered.length / ctx.size));
  ctx.page = Math.min(ctx.page, totalPages);
  const shown = new Set(
    filtered.slice((ctx.page - 1) * ctx.size, ctx.page * ctx.size),
  );
  const matched = new Set(filtered);
  ctx.table.tBodies[0].replaceChildren(
    ...filtered,
    ...ctx.rows.filter((row) => !matched.has(row)),
  );
  ctx.rows.forEach((row) => {
    row.hidden = !shown.has(row);
  });
  if (!filtered.length) ctx.table.tBodies[0].append(ctx.empty);
  ctx.count.textContent = `Mostrando ${filtered.length ? (ctx.page - 1) * ctx.size + 1 : 0}–${Math.min(ctx.page * ctx.size, filtered.length)} de ${filtered.length} proyectos`;
  const move = (next) => {
    ctx.page = next;
    ctx.render();
  };
  ctx.pages.replaceChildren(
    el("button", {
      type: "button",
      "aria-label": "Histórico IXB página anterior",
      text: "‹",
      disabled: ctx.page === 1,
      onclick: () => move(ctx.page - 1),
    }),
    el("span", {
      class: "eva-history-current",
      "aria-current": "page",
      text: `${ctx.page} / ${totalPages}`,
    }),
    el("button", {
      type: "button",
      "aria-label": "Histórico IXB página siguiente",
      text: "›",
      disabled: ctx.page === totalPages,
      onclick: () => move(ctx.page + 1),
    }),
  );
}
