import test from "node:test";
import assert from "node:assert/strict";
import { matchesColumn as matches } from "../../frontend/static/scripts/pages/eva3/column_menu_model.js";
test("numeric and date conditions keep unavailable values out", () => {
  assert.equal(
    matches("Sin dato", null, "none", { condition: "gt", first: "0" }),
    false,
  );
  assert.equal(
    matches("62", 62, "green", {
      condition: "between",
      first: "60",
      second: "65",
    }),
    true,
  );
  assert.equal(
    matches("62", 62, "green", { condition: "lte", first: "60" }),
    false,
  );
  assert.equal(
    matches("20/02/26", "2026-02-20", "none", {
      condition: "gte",
      first: "2026-02-01",
    }),
    true,
  );
  assert.equal(
    matches("20/01/26", "2026-01-20", "none", {
      condition: "gte",
      first: "2026-02-01",
    }),
    false,
  );
});
test("value selections and color are combined with the condition", () => {
  const filter = {
    values: new Set(["Nestlé"]),
    color: "green",
    condition: "contains",
    first: "nestle",
  };
  assert.equal(matches("Nestlé", "Nestlé", "green", filter), true);
  assert.equal(matches("Nestlé", "Nestlé", "red", filter), false);
  assert.equal(matches("Otra", "Otra", "green", filter), false);
  assert.equal(
    matches("Nestlé", "Nestlé", "green", { values: new Set() }),
    false,
  );
  assert.equal(matches("", "", "none", { condition: "empty" }), true);
});
