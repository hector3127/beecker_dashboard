// @ts-check
// DOM presentation; state and reload callbacks belong to the controller.
import { el } from "#app/lib/dom.js";

/** @param {Record<string, any>} ctx Live state and controller callbacks. */
export function renderReference(ctx) {
  const result = ctx.filtered(),
    totalPages = Math.max(1, Math.ceil(result.length / ctx.size));
  ctx.page = Math.min(ctx.page, totalPages);
  const shown = new Set(
    result.slice((ctx.page - 1) * ctx.size, ctx.page * ctx.size),
  );
  const matches = new Set(result);
  ctx.table.tBodies[0].replaceChildren(
    ...result,
    ...ctx.rows.filter((row) => !matches.has(row)),
    ...(ctx.totals ? [ctx.totals] : []),
  );
  ctx.rows.forEach((row) => {
    row.hidden = !shown.has(row);
  });
  if (!result.length && !ctx.totals)
    ctx.table.tBodies[0].append(
      el(
        "tr",
        { class: "eva4-no-results" },
        el("td", {
          colspan: ctx.table.tHead.querySelectorAll("th[scope=col]").length,
          text: "Sin resultados.",
        }),
      ),
    );
  ctx.count.textContent = `Mostrando ${shown.size} de ${result.length} ${ctx.unit}`;
  const move = (next) => {
    ctx.page = next;
    ctx.render();
  };
  const numbers = Array.from({ length: totalPages }, (_, i) => i + 1).filter(
    (n) => n === 1 || n === totalPages || Math.abs(n - ctx.page) <= 1,
  );
  const buttons = [];
  numbers.forEach((n, i) => {
    if (i && n - numbers[i - 1] > 1) buttons.push(el("span", { text: "…" }));
    buttons.push(
      el("button", {
        type: "button",
        "aria-label": `${ctx.kind} página ${n}`,
        "aria-current": ctx.page === n ? "page" : null,
        text: n,
        onclick: () => move(n),
      }),
    );
  });
  ctx.nav.replaceChildren(
    el("button", {
      type: "button",
      "aria-label": `${ctx.kind} página anterior`,
      text: "‹",
      disabled: ctx.page === 1,
      onclick: () => move(ctx.page - 1),
    }),
    ...buttons,
    el("button", {
      type: "button",
      "aria-label": `${ctx.kind} página siguiente`,
      text: "›",
      disabled: ctx.page === totalPages,
      onclick: () => move(ctx.page + 1),
    }),
  );
  ctx.onCount({ shown: result.length, total: ctx.rows.length });
  return { shown: result.length, total: ctx.rows.length };
}
