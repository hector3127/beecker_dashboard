import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import { accountInitials } from "../../frontend/static/scripts/pages/eva1/account_column_model.js";
import { monthlyValues } from "../../frontend/static/scripts/pages/executive/sections/card_visuals_model.js";
import {
  number,
  fmt,
} from "../../frontend/static/scripts/pages/billability/reference_model.js";
import { csvCell } from "../../frontend/static/scripts/pages/eva4/report_table_model.js";
import { presentation } from "../../frontend/static/scripts/pages/dictionary/presentation_model.js";

test("account initials retain original spacing, accents and missing-name fallback", () => {
  assert.equal(accountInitials("  Clínica   del Sur  "), "CD");
  assert.equal(accountInitials("área"), "Á");
  assert.equal(accountInitials("   "), "—");
});
test("monthly card values preserve numeric text, zero, absent costs and negative margins", () => {
  const months = [
    { revenue: "100", cost: "70" },
    { revenue: 0, cost: 3 },
    { revenue: "", cost: 2 },
    { revenue: "20", cost: null },
    { revenue: 50, cost: 100 },
  ];
  assert.deepEqual(monthlyValues(months, false), [100, 0, null, 20, 50]);
  assert.deepEqual(monthlyValues(months, true), [30, null, null, null, -100]);
});
test("billability parsing preserves decimal comma and unavailable values", () => {
  assert.equal(number("12,5"), 12.5);
  assert.equal(number(""), null);
  assert.equal(number(null), null);
  assert.equal(number("Pendiente"), null);
  assert.equal(fmt(0), "0");
  assert.equal(fmt(null), "—");
});
test("report CSV keeps formula protection, quotes and missing values", () => {
  assert.equal(csvCell("=1+1"), '"\'=1+1"');
  assert.equal(csvCell('a"b'), '"a""b"');
  assert.equal(csvCell(null), '""');
  assert.equal(csvCell(0), '"0"');
});
test("dictionary presentation retains every sentence and the original category", () => {
  const value = presentation({
    name: "Importes",
    definition: "Primera. Segunda. Tercera.",
  });
  assert.equal(value.category, "Finanzas");
  assert.equal(value.definition, "Primera. Segunda.");
  assert.equal(value.notes, "Tercera.");
});
test("extracted models have no DOM, view or transport dependencies", () => {
  const names = [
    "eva1/account_column_model",
    "eva1/history_table_model",
    "eva3/column_menu_model",
    "eva3/history_reference_model",
    "eva3/reference_model",
    "eva4/report_table_model",
    "billability/reference_model",
    "dictionary/presentation_model",
    "executive/sections/card_visuals_model",
    "operativa/sections/capacity_model",
    "operativa/sections/eva_model",
  ];
  for (const name of names) {
    const source = fs.readFileSync(
      `frontend/static/scripts/pages/${name}.js`,
      "utf8",
    );
    assert.doesNotMatch(
      source,
      /\bdocument\b|\bwindow\b|\bfetch\s*\(|_view\.js|api-client|lib\/dom/,
      name,
    );
    assert.match(source, /^\/\/ @ts-check/, name);
  }
});

test("all 17 integration entries enable checking and keep reads on the API client", () => {
  const names = [
    "eva1/account_column",
    "eva1/history_table",
    "eva1/main",
    "eva1/model",
    "eva3/column_menu",
    "eva3/history_reference",
    "eva3/main",
    "eva3/model",
    "eva3/reference",
    "eva/history",
    "eva/table_columns",
    "eva4/report_table",
    "executive/sections/card_visuals",
    "billability/reference",
    "operativa/sections/capacity",
    "operativa/sections/eva",
    "dictionary/presentation",
  ];
  for (const name of names) {
    const source = fs.readFileSync(
      `frontend/static/scripts/pages/${name}.js`,
      "utf8",
    );
    assert.match(source, /^\/\/ @ts-check/, name);
    assert.doesNotMatch(source, /\bfetch\s*\(/, name);
  }
});
