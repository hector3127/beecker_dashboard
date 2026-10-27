import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {
  chartsModel,
  barsModel,
  palette,
} from "../../frontend/static/scripts/pages/project_detail/sections/generic_charts_model.js";
const frozen = JSON.parse(
  fs.readFileSync(
    new URL("./frozen/generic_charts.json", import.meta.url),
    "utf8",
  ),
);
test("area geometry, offsets and rounded total match the original SVG", () => {
  assert.equal(frozen.areas.length, 5);
  assert.deepEqual(palette, frozen.palette);
  for (const { input, geometry, label } of frozen.areas) {
    const data = structuredClone(input),
      model = chartsModel(data);
    assert.deepEqual(
      model.areas.map((x) => [x.dash, String(x.offset)]),
      geometry,
    );
    assert.equal(String(model.total), label);
    assert.deepEqual(data, input);
  }
});
test("bars keep the full-list scale including hidden rows and original widths", () => {
  assert.equal(frozen.bars.length, 2);
  for (const { input, widths } of frozen.bars) {
    const items = structuredClone(input);
    assert.equal(items.length, 8);
    assert.deepEqual(
      barsModel(items).flatMap((x) => [String(x.estimated), String(x.real)]),
      widths,
    );
    assert.equal(barsModel(items)[1].estimated, 0.3);
    assert.deepEqual(items, input);
  }
});

test("resource order/role order, labels, palette cycle and empty data stay unchanged", () => {
  const data = {
    distribucionArea: Array.from({ length: 8 }, (_, i) => ({
      nombre: "A" + i,
      horas: 1,
      pct: 12.5,
    })),
    filasRecursosCompleto: [
      { nombre: "A", posicion: "Dev", horasEstimadas: 1, horasReales: 1 },
      { nombre: "B", posicion: "", horasEstimadas: 2, horasReales: 3 },
    ],
    porRol: [{ rol: "QA", horasEstimadas: 4, horasReales: 2 }],
  };
  const before = structuredClone(data),
    model = chartsModel(data);
  assert.deepEqual(
    model.resources.map((x) => x.name),
    ["B", "A — Dev"],
  );
  assert.deepEqual(
    model.roles.map((x) => x.name),
    ["QA"],
  );
  assert.equal(model.areas[6].color, palette[0]);
  assert.deepEqual(chartsModel({ distribucionArea: [] }), {
    areas: [],
    total: 0,
    resources: [],
    roles: [],
  });
  assert.deepEqual(data, before);
});
