// @ts-check
import { mountAccountColumn } from "./account_column.js";
import { mountIxbHistory } from "./history_table.js";
import { mountTableColumns, cellText } from "../eva/table_columns.js";
import { mountHistory } from "../eva/history.js";
import { matches, csv, headers } from "./model.js";
import { watchLoadingMessages } from "#app/ui/portal-loading.js";

watchLoadingMessages();

const table = document.getElementById("eva-table");
if (table) {
  const rows = [...table.querySelectorAll("tbody tr[data-manager]")];
  mountAccountColumn(table, rows);
  const controls = Object.fromEntries(
    ["manager", "service", "from", "to"].map((key) => [
      key,
      document.getElementById("eva-" + key),
    ]),
  );
  let columns;
  function filter() {
    columns?.sort(rows).forEach((row) => table.tBodies[0].append(row));
    let count = 0;
    for (const row of rows) {
      row.hidden =
        !(columns?.matches(row) ?? true) ||
        !matches(
          row.dataset,
          Object.fromEntries(
            Object.entries(controls).map(([key, control]) => [
              key,
              control.value,
            ]),
          ),
        );
      if (!row.hidden) count++;
    }
    document.getElementById("eva-count").textContent =
      "Mostrando " + count + " de " + rows.length + " proyectos";
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
    control.addEventListener("change", filter),
  );
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
document
  .querySelector("[data-eva-refresh]")
  .addEventListener("click", () => location.reload());
mountHistory({
  box: document.getElementById("eva-closed-box"),
  body: document.getElementById("eva-closed-body"),
  path: "screens/eva-1/cerrados/",
  afterLoad: mountIxbHistory,
});
