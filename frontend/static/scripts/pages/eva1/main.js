// @ts-check
import { mountAccountColumn } from "./account_column.js";
import { mountIxbHistory } from "./history_table.js";
import { mountTableColumns, cellText } from "../eva/table_columns.js";
import { mountHistory } from "../eva/history.js";
import { csv, headers } from "./model.js";
import { watchLoadingMessages } from "#app/ui/portal-loading.js";
import { mountExtraction } from './extraction.js';

watchLoadingMessages();
mountExtraction();

const table = document.getElementById("eva-table");
if (table) {
  const rows = [...table.querySelectorAll("tbody tr[data-manager]")];
  mountAccountColumn(table, rows);
  const controls = Object.fromEntries(
    ["manager", "service"].map((key) => [
      key,
      document.getElementById("eva-" + key),
    ]),
  );
  const query = new URLSearchParams(location.search);
  const filterKeys = { manager: "manager", service: "service" };
  for (const [key, control] of Object.entries(controls)) {
    control.value = query.get(filterKeys[key]) || "";
  }
  let columns;
  function filter() {
    columns?.sort(rows).forEach((row) => table.tBodies[0].append(row));
    let count = 0;
    for (const row of rows) {
      row.hidden = !(columns?.matches(row) ?? true);
      if (!row.hidden) count++;
    }
    document.getElementById("eva-count").textContent =
      "Mostrando " +
      count +
      " de " +
      document.getElementById("eva-count").dataset.total +
      " proyectos";
    const url = new URL(location.href);
    for (const [key, control] of Object.entries(controls)) {
      if (control.value) url.searchParams.set(filterKeys[key], control.value);
      else url.searchParams.delete(filterKeys[key]);
    }
    history.replaceState(null, "", url);
  }
  columns = mountTableColumns({
    table,
    rows,
    types: Object.fromEntries(
      Array.from({ length: 27 }, (_, index) => [
        index,
        [6, 7].includes(index) ? "date" : index >= 8 ? "number" : "text",
      ]),
    ),
    onChange: filter,
  });
  Object.values(controls).forEach((control) =>
    control.addEventListener("change", () => consult(false)),
  );
  filter();
  document.getElementById("eva-export").addEventListener("click", () => {
    const content = csv(
      columns
        .sort(rows)
        .filter((row) => !row.hidden)
        .map((row) =>
          [...row.cells]
            .map(cellText)
            .map((value) => (/^[=+@-]/.test(value) ? "'" + value : value)),
        ),
      [headers[0], "Cuenta", ...headers.slice(1)],
    );
    const url = URL.createObjectURL(
      new Blob(["\uFEFF" + content], { type: "text/csv;charset=utf-8" }),
    );
    const a = document.createElement("a");
    a.href = url;
    a.download = "EVA1_IXB_RaaS.csv";
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
}
/** @param {boolean} applyDate Only the explicit button applies an edited cut. */
function consult(applyDate) {
  const cut = document.getElementById("eva-cut");
  if (!cut.reportValidity()) return;
  const url = new URL(location.href);
  if (applyDate || url.searchParams.has("corte"))
    url.searchParams.set(
      "corte",
      applyDate ? cut.value : url.searchParams.get("corte"),
    );
  for (const name of ["manager", "service"]) {
    const value = document.getElementById("eva-" + name).value;
    if (value) url.searchParams.set(name, value);
    else url.searchParams.delete(name);
  }
  url.searchParams.delete("desde");
  url.searchParams.delete("hasta");
  location.assign(url.href);
}
document
  .querySelector("[data-eva-refresh]")
  .addEventListener("click", () => consult(true));
mountHistory({
  box: document.getElementById("eva-closed-box"),
  body: document.getElementById("eva-closed-body"),
  path: "screens/eva-1/cerrados/",
  afterLoad: mountIxbHistory,
});
