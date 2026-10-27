import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import {
  projectParams,
  metadata,
  family,
} from "../../frontend/static/scripts/pages/project_detail/sections/project_entry_model.js";

const source = fs.readFileSync(
  "tests/reference/static/portal/js/proyecto_detalle.js",
  "utf8",
);
test("project route seed retains priority over query and keeps return filters", () => {
  const params = projectParams(
    "?proyecto=OTHER&volver=%2Fcuenta%2Foxxo%2F&cuenta=Oxxo",
    '{"id":"AER.001"}',
  );
  assert.equal(params.get("proyecto"), "AER.001");
  assert.equal(params.get("volver"), "/cuenta/oxxo/");
  assert.equal(params.get("cuenta"), "Oxxo");
  assert.equal(projectParams("?proyecto=IXB.001").get("proyecto"), "IXB.001");
});
test("metadata preserves original keys, references and last duplicate", () => {
  const first = { id: "1", servicio: "AER" },
    last = { id: "1", servicio: "IXB" };
  assert.deepEqual(metadata({}), {});
  assert.equal(metadata({ proyectos: [first, last] })["1"], last);
  assert.equal(metadata({ proyectos: [first] })["1"], first);
});
for (const service of [
  "AER",
  "T&M",
  "TYM",
  "IXB",
  "SaaS",
  "RaaS",
  "",
  "OTHER",
  "  i-x-b  ",
]) {
  test(`family matches original service rules: ${service || "missing"}`, () => {
    for (const id of ["AER.001", "TYM.001", "AMK.008", "other"]) {
      const map = { [id]: { servicio: service } };
      const scope = { mapaMetaProyectosDashboard: map };
      for (const name of ["_esProyectoAERTYM", "_ixsEsServicio"])
        vm.runInNewContext(
          source.match(
            new RegExp(`  function ${name}\\([\\s\\S]*?\\n  \\}`),
          )[0],
          scope,
        );
      assert.equal(
        family(id, map),
        scope._esProyectoAERTYM(id)
          ? "aer"
          : scope._ixsEsServicio(id)
            ? "ixs"
            : "executive",
      );
    }
  });
}
