import { mountHistory } from "../eva/history.js";
import { matches, csv } from "./model.js";
import { watchLoadingMessages } from "#app/ui/portal-loading.js";

watchLoadingMessages();

const table = document.getElementById("eva-table");
if (table) {
  const rows = [...table.querySelectorAll("tbody tr[data-manager]")];
  const controls = Object.fromEntries(
    ["manager", "service", "from", "to"].map((key) => [
      key,
      document.getElementById("eva-" + key),
    ]),
  );
  function filter() {
    let count = 0;
    for (const row of rows) {
      row.hidden = !matches(
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
  Object.values(controls).forEach((control) =>
    control.addEventListener("change", filter),
  );
  document.getElementById("eva-export").addEventListener("click", () => {
    const content = csv(
      rows
        .filter((row) => !row.hidden)
        .map((row) => [...row.cells].map((cell) => cell.innerText.trim())),
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
});
