// Explicit original-only capture; temporary until tests/reference is retired.
import fs from "node:fs";
import vm from "node:vm";
const source = fs.readFileSync(
  "tests/reference/static/portal/js/proyecto_detalle.js",
  "utf8",
);
const pick = (name) =>
  source.match(new RegExp(String.raw`  function ${name}\([\s\S]*?\n  \}`))[0];
const scope = {};
for (const name of [
  "_aerClienteNivelClase",
  "_aerClienteInitials",
  "_aerClienteCsv",
  "_aerNormFilter",
])
  vm.runInNewContext(pick(name), scope);
const helpers = {};
for (const [label, fn, inputs] of [
  ["levels", "_aerClienteNivelClase", ["Alto", "medio", "Bajo", "", null, "x"]],
  [
    "initials",
    "_aerClienteInitials",
    ["Ana Pérez", "  luis  soto gil ", "", null, "x"],
  ],
  ["csv", "_aerClienteCsv", ['a"b', null, 12, "x,y"]],
  ["normalize", "_aerNormFilter", ["ÁÉÍ  Ñu ", null, "Hola"]],
])
  helpers[label] = inputs.map((input) => ({
    input,
    expected: scope[fn](input),
  }));
fs.writeFileSync(
  "tests/frontend/frozen/client_helpers.json",
  JSON.stringify(helpers, null, 2) + "\n",
);

const services = [
  "AER",
  "T&M",
  "TYM",
  "IXB",
  "SaaS",
  "RaaS",
  "",
  "OTHER",
  "  i-x-b  ",
];
const families = services.map((service) => ({
  service,
  cases: ["AER.001", "TYM.001", "AMK.008", "other"].map((id) => {
    const map = { [id]: { servicio: service } };
    const original = { mapaMetaProyectosDashboard: map };
    for (const name of ["_esProyectoAERTYM", "_ixsEsServicio"])
      vm.runInNewContext(pick(name), original);
    return {
      id,
      map,
      expected: original._esProyectoAERTYM(id)
        ? "aer"
        : original._ixsEsServicio(id)
          ? "ixs"
          : "executive",
    };
  }),
}));
fs.writeFileSync(
  "tests/frontend/frozen/project_entry_families.json",
  JSON.stringify(families, null, 2) + "\n",
);

const progress = [];
for (const dev of [0, "", 60, "45.5", -10, 125, "invalid", null])
  for (const qa of [true, false]) {
    const cell = { innerHTML: "" };
    const row = {
      querySelector: (selector) =>
        selector.includes("5") ? { value: dev } : { checked: qa },
    };
    const original = {
      document: {
        getElementById: (id) => (id.startsWith("wi-row") ? row : cell),
      },
    };
    vm.runInNewContext(pick("_recalcularAvanceFilaWorkItem"), original);
    original._recalcularAvanceFilaWorkItem(101);
    const expected = Number(
      cell.innerHTML.match(/progress-bar-fill[\s\S]*?width:([^%]+)%/)[1],
    );
    if (!Number.isFinite(expected))
      throw Error("Unexpected non-finite progress");
    progress.push({ dev, qa, expected });
  }
fs.writeFileSync(
  "tests/frontend/frozen/ixs_work_items.json",
  JSON.stringify(progress, null, 2) + "\n",
);
console.log(
  "Captured 18 contact helper outputs, 36 families and 16 work item progress values.",
);

const initialStates = {};
for (const name of ["aerIAState", "ixsIAState"]) {
  const literal = source.match(
    new RegExp(
      `var ${name} = window\\.beeProjectState \\? window\\.beeProjectState\\.\\w+ : (\\{[^\\n]+\\});`,
    ),
  )[1];
  initialStates[name] = vm.runInNewContext(`(${literal})`);
}
fs.writeFileSync(
  "tests/frontend/frozen/project_session_initial.json",
  JSON.stringify(initialStates, null, 2) + "\n",
);
console.log("Captured two original initial session states.");
