// @ts-check
// DOM presentation; state and reload callbacks belong to the controller.
import { el } from "#app/lib/dom.js";

import { text } from "./history_reference_view.js";
/** @param {Record<string, any>} ctx Live state and controller callbacks. */
export function renderReference(ctx) {
  const result = ctx.filtered(),
    totalPages = Math.max(1, Math.ceil(result.length / ctx.size));
  ctx.page = Math.min(ctx.page, totalPages);
  const shown = new Set(
    result
      .slice((ctx.page - 1) * ctx.size, ctx.page * ctx.size)
      .map((record) => record.row),
  );
  // Reuse actual nodes so asynchronous consumption and retry handlers stay attached.
  ctx.table.tBodies[0].replaceChildren(
    ...result.map((record) => record.row),
    ...ctx.records
      .filter((record) => !result.includes(record))
      .map((record) => record.row),
  );
  ctx.records.forEach((record) => {
    record.row.hidden = !shown.has(record.row);
  });
  if (!result.length) ctx.table.tBodies[0].append(ctx.empty);
  ctx.count.textContent = `Mostrando ${shown.size} de ${result.length} proyectos`;
  ctx.table.querySelectorAll("thead th").forEach((th, index) => {
    th.setAttribute(
      "aria-sort",
      ctx.sortIndex === index
        ? ctx.direction === 1
          ? "ascending"
          : "descending"
        : "none",
    );
    th.classList.toggle("eva3-column-filtered", ctx.filters.has(index));
    th.querySelector("button").setAttribute(
      "aria-label",
      `Opciones de ${th.dataset.label}${ctx.filters.has(index) ? ", filtro aplicado" : ""}`,
    );
  });
  const numbers = Array.from(
    { length: totalPages },
    (_, index) => index + 1,
  ).filter(
    (number) =>
      number === 1 || number === totalPages || Math.abs(number - ctx.page) <= 1,
  );
  const buttons = [];
  numbers.forEach((number, index) => {
    if (index && number - numbers[index - 1] > 1)
      buttons.push(el("span", { text: "…" }));
    buttons.push(
      el("button", {
        type: "button",
        "aria-label": `Histórico página ${number}`,
        "aria-current": number === ctx.page ? "page" : null,
        text: number,
        onclick: () => {
          ctx.page = number;
          ctx.render();
        },
      }),
    );
  });
  ctx.pages.replaceChildren(
    el("button", {
      type: "button",
      text: "‹",
      "aria-label": "Histórico página anterior",
      disabled: ctx.page === 1,
      onclick: () => {
        ctx.page--;
        ctx.render();
      },
    }),
    ...buttons,
    el("button", {
      type: "button",
      text: "›",
      "aria-label": "Histórico página siguiente",
      disabled: ctx.page === totalPages,
      onclick: () => {
        ctx.page++;
        ctx.render();
      },
    }),
  );
}
