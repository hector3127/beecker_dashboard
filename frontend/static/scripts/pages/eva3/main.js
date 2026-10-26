import { mountHistoryReference } from "./history_reference.js";
import { mountReference } from "./reference.js";
import { apiSend } from "#app/data/api-client.js";
import { el } from "#app/lib/dom.js";
import { mountHistory } from "../eva/history.js";
import { fmt, etc, advance, averageCost } from "./model.js";
import { watchLoadingMessages } from "#app/ui/portal-loading.js";

watchLoadingMessages();
mountReference();

function badge(cell, value, bad, suffix = "") {
  cell.replaceChildren(
    el("span", {
      class: "bd " + (bad ? "bad" : "ok"),
      text: fmt(value) + suffix,
    }),
  );
}
async function fillActive() {
  const rows = [...document.querySelectorAll("tr[data-project]")];
  function cost() {
    const cell = document.getElementById("eva3-cost");
    if (cell) cell.textContent = averageCost(rows.map((row) => row.dataset));
  }
  const pending = rows.filter((row) => row.dataset.burn === "");
  for (const row of pending) {
    const cell = row.querySelector('[data-field="burn"]');
    cell.textContent = "Consultando…";
    cell.classList.add("loading");
  }
  for (let i = 0; i < pending.length; i += 2) {
    const batch = pending.slice(i, i + 2);
    try {
      const { data: result } = await apiSend(
        "POST",
        "screens/eva-3/consumos/",
        { proyectos: batch.map((row) => row.dataset.project) },
        { timeout: 90000 },
      );
      if (!result?.ok)
        throw Error(result?.error || "No se pudieron consultar las horas");
      for (const row of batch) {
        const item = (result.items || []).find(
          (value) =>
            String(value.id).toLowerCase() ===
            row.dataset.project.toLowerCase(),
        );
        if (typeof item?.burn !== "number" || !Number.isFinite(item.burn))
          throw Error(item?.error || "Consumo no disponible");
        const budget = Number(row.dataset.budget);
        row.dataset.burn = String(item.burn);
        const cell = row.querySelector('[data-field="burn"]');
        cell.textContent = fmt(item.burn);
        cell.classList.remove("loading");
        const remaining = etc(budget, item.burn);
        badge(
          row.querySelector('[data-field="etc"]'),
          remaining,
          remaining <= 0,
        );
        if (budget > 0) {
          const progress = advance(budget, item.burn);
          badge(
            row.querySelector('[data-field="progress"]'),
            progress,
            progress > 100,
            "%",
          );
        }
      }
    } catch (error) {
      for (const row of batch) {
        if (row.dataset.burn !== "") continue;
        const cell = row.querySelector('[data-field="burn"]');
        cell.textContent = "No disponible";
        cell.title = error.message;
        cell.className = "clock-error";
      }
    }
    cost();
    document.getElementById('eva3-projects')?.dispatchEvent(new Event('eva3-active-updated'));
  }
}
async function fillHistoricBurn(body) {
  const pending = [...body.querySelectorAll("tr[data-missing-burn]")];
  async function fill(row) {
    const cell = row.querySelector('[data-closed-field="burn"]');
    cell.textContent = "Consultando...";
    try {
      const { data: result } = await apiSend(
        "POST",
        "screens/eva-3/cerrados/consumo/",
        { id: row.dataset.closedId },
        { timeout: 90000 },
      );
      if (typeof result.burn !== "number")
        throw Error(result.error || "Consumo no disponible");
      const budget = Number(row.dataset.budget);
      badge(cell, result.burn, result.burn > budget);
      cell.title = "Guardado en MPB";
      badge(
        row.querySelector('[data-closed-field="etc"]'),
        budget - result.burn,
        budget - result.burn < 0,
      );
      const progress = row.querySelector('[data-closed-field="progress"]');
      if (budget > 0)
        badge(
          progress,
          (result.burn / budget) * 100,
          result.burn > budget,
          "%",
        );
      else progress.textContent = "Sin dato";
      row.removeAttribute("data-missing-burn");
    } catch (error) {
      cell.textContent = "No disponible";
      cell.title = error.message;
      cell.append(
        " ",
        el("button", {
          type: "button",
          text: "Reintentar",
          onclick: () => fill(row),
        }),
      );
    } finally {
      body.dispatchEvent(new Event("eva3-history-updated"));
    }
  }
  await Promise.all(
    [0, 1].map(async () => {
      while (pending.length) await fill(pending.shift());
    }),
  );
}
fillActive();
mountHistory({
  box: document.getElementById("eva3-closed-box"),
  body: document.getElementById("eva3-closed-body"),
  path: "screens/eva-3/cerrados/",
  aer: true,
  afterLoad: (body) => {mountHistoryReference(body); fillHistoricBurn(body);},
});
