import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import {
  chartsModel,
  barsModel,
  palette,
} from "../../frontend/static/scripts/pages/project_detail/sections/generic_charts_model.js";
const source = fs.readFileSync(
  "tests/reference/static/portal/js/proyecto_detalle.js",
  "utf8",
);
const original = (name) =>
  source.match(new RegExp(`  function ${name}\\([\\s\\S]*?\\n  \\}`))[0];
function render(name, args) {
  const nodes = {};
  const document = {
    getElementById: (id) => (nodes[id] ||= { innerHTML: "", style: {} }),
  };
  vm.runInNewContext(`${original(name)};${name}(...args);`, {
    document,
    args,
    PALETA_DONUT: palette,
    COLOR_ESTIMADA: "#C9C9CC",
    COLOR_REAL: "var(--vino)",
  });
  return nodes.chart.innerHTML;
}
test("area geometry, offsets and rounded total match the original SVG", () => {
  for (const hours of [
    [2.5, 3.25, 0],
    [0, 0],
    [0.04, 0.04],
    [-1, 3],
    [5, -2],
  ]) {
    const data = {
      distribucionArea: hours.map((horas, i) => ({
        nombre: "A" + i,
        horas,
        pct: 17,
      })),
    };
    const before = structuredClone(data),
      model = chartsModel(data);
    const total = Math.round(hours.reduce((a, b) => a + b, 0) * 10) / 10;
    const html = render("renderDonut", [
      "chart",
      data.distribucionArea,
      total,
      palette,
    ]);
    assert.deepEqual(
      model.areas.map((x) => [x.dash, String(x.offset)]),
      [
        ...html.matchAll(
          /stroke-dasharray="([^"]*)" stroke-dashoffset="([^"]*)"/g,
        ),
      ].map((x) => [x[1], x[2]]),
    );
    assert.ok(html.includes(`>${model.total}</text>`));
    assert.deepEqual(data, before);
  }
});
test("bars keep the full-list scale including hidden rows and original widths", () => {
  const items = Array.from({ length: 8 }, (_, i) => ({
    nombre: "R" + i,
    horasEstimadas: i === 7 ? 1000 : i * 3,
    horasReales: i - 1,
  }));
  for (const name of ["renderComparativo", "renderComparativoConVerTodos"]) {
    const html = render(name, ["chart", items]);
    assert.deepEqual(
      barsModel(items).flatMap((x) => [String(x.estimated), String(x.real)]),
      [...html.matchAll(/class="barra-fill" style="width:([^%]+)%;/g)].map(
        (x) => x[1],
      ),
    );
  }
  assert.equal(barsModel(items)[1].estimated, 0.3);
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
