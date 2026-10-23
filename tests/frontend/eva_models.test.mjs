import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import {
  date,
  matches,
  csv,
} from "../../frontend/static/scripts/pages/eva1/model.js";
import { averageCost } from "../../frontend/static/scripts/pages/eva3/model.js";

const original1 = fs
  .readFileSync("apps/portal/templates/portal/eva1.html", "utf8")
  .match(/<script>([\s\S]*?)<\/script>/)[1];
test("EVA1 filters and CSV match the previous inline script", async () => {
  let blob;
  const rows = [
    {
      dataset: {
        manager: "Laura",
        service: "RaaS",
        start: "01/01/26",
        end: "30/09/26",
      },
      cells: [{ innerText: "Laura" }, { innerText: 'Proyecto, "A"' }],
    },
    {
      dataset: { manager: "Mario", service: "IXB", start: "", end: "" },
      cells: [{ innerText: "Mario" }, { innerText: "P2" }],
    },
  ];
  const controls = Object.fromEntries(
    ["eva-manager", "eva-service", "eva-from", "eva-to"].map((id) => [
      id,
      { value: "", addEventListener() {} },
    ]),
  );
  controls["eva-count"] = {};
  controls["eva-export"] = {
    addEventListener(_, fn) {
      this.run = fn;
    },
  };
  const context = {
    document: {
      getElementById: (id) =>
        id === "eva-table" ? { querySelectorAll: () => rows } : controls[id],
      createElement: () => ({ click() {} }),
    },
    URL: {
      createObjectURL(value) {
        blob = value;
        return "blob:test";
      },
      revokeObjectURL() {},
    },
    Blob,
    setTimeout() {},
  };
  vm.runInNewContext(
    original1.replace("})();", "globalThis.oracle={date,filter};})();"),
    context,
  );
  for (const filters of [
    { manager: "", service: "", from: "", to: "" },
    { manager: "Mario", service: "", from: "", to: "" },
    { manager: "", service: "RaaS", from: "2026-10-01", to: "" },
    { manager: "", service: "IXB", from: "2027-01-01", to: "2027-02-01" },
  ]) {
    for (const [key, value] of Object.entries(filters))
      controls["eva-" + key].value = value;
    context.oracle.filter();
    assert.deepEqual(
      rows.map((row) => !row.hidden),
      rows.map((row) => matches(row.dataset, filters)),
    );
    controls["eva-export"].run();
    const expected = new Blob([
      "\ufeff" +
        csv(
          rows
            .filter((row) => !row.hidden)
            .map((row) => row.cells.map((c) => c.innerText.trim())),
        ),
    ]);
    assert.equal(await blob.text(), await expected.text());
  }
  for (const value of ["", "01/02/26", "malformed", "01/02/2026"])
    assert.equal(date(value), context.oracle.date(value));
});

const original3 = fs.readFileSync(
  "apps/portal/templates/portal/eva3.html",
  "utf8",
);
test("EVA3 average keeps pending rows and zero budgets out like the previous screen", () => {
  const start = original3.indexOf("function cost(){"),
    end = original3.indexOf("const pending=", start);
  for (const rows of [
    [],
    [{ budget: "100", burn: "" }],
    [
      { budget: "100", burn: "120" },
      { budget: "0", burn: "50" },
      { budget: "200", burn: "50" },
      { budget: "50", burn: "" },
    ],
  ]) {
    const output = {};
    const context = {
      rows: rows.map((dataset) => ({ dataset })),
      document: { getElementById: () => output },
      fmt: (n) => n.toLocaleString("es-MX", { maximumFractionDigits: 2 }),
    };
    vm.runInNewContext(original3.slice(start, end) + "cost();", context);
    assert.equal(averageCost(rows), output.textContent);
  }
});
