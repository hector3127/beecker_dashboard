// Temporary explicit original renderer capture. No current model imports.
import fs from "node:fs";
import vm from "node:vm";
const source = fs.readFileSync(
  "tests/reference/static/portal/js/proyecto_detalle.js",
  "utf8",
);
const pick = (name) =>
  source.match(new RegExp(`  function ${name}\\([\\s\\S]*?\\n  \\}`))[0];
const palette = vm.runInNewContext(
  source.match(/  const PALETA_BEECKER = ([^\n]+);/)[1],
);
function render(name, args) {
  const nodes = {};
  const document = {
    getElementById: (id) => (nodes[id] ||= { innerHTML: "", style: {} }),
  };
  vm.runInNewContext(`${pick(name)};${name}(...args);`, {
    document,
    args,
    PALETA_DONUT: palette,
    COLOR_ESTIMADA: "#C9C9CC",
    COLOR_REAL: "var(--vino)",
  });
  return nodes.chart.innerHTML;
}
const areas = [
  [2.5, 3.25, 0],
  [0, 0],
  [0.04, 0.04],
  [-1, 3],
  [5, -2],
].map((hours) => {
  const input = {
    distribucionArea: hours.map((horas, i) => ({
      nombre: "A" + i,
      horas,
      pct: 17,
    })),
  };
  const total = Math.round(hours.reduce((a, b) => a + b, 0) * 10) / 10;
  const html = render("renderDonut", [
    "chart",
    input.distribucionArea,
    total,
    palette,
  ]);
  const geometry = [
    ...html.matchAll(/stroke-dasharray="([^"]*)" stroke-dashoffset="([^"]*)"/g),
  ].map((x) => [x[1], x[2]]);
  const label = html.match(
    /class="donut-center-value"[^>]*>([^<]*)<\/text>/,
  )[1];
  return { input, geometry, label };
});
const items = Array.from({ length: 8 }, (_, i) => ({
  nombre: "R" + i,
  horasEstimadas: i === 7 ? 1000 : i * 3,
  horasReales: i - 1,
}));
const bars = ["renderComparativo", "renderComparativoConVerTodos"].map(
  (name) => {
    const html = render(name, ["chart", items]);
    return {
      name,
      input: items,
      widths: [
        ...html.matchAll(/class="barra-fill" style="width:([^%]+)%;/g),
      ].map((x) => x[1]),
    };
  },
);
fs.writeFileSync(
  "tests/frontend/frozen/generic_charts.json",
  JSON.stringify({ palette, areas, bars }, null, 2) + "\n",
);
console.log(
  "Captured original palette, 5 SVG geometries/labels and 2 full-list bar renderings.",
);
