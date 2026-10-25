import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import {
  initialAerAi,
  initialIxsAi,
  selectAerAi,
  selectIxsAi,
  selectClockify,
  outdatedAer,
} from "../../frontend/static/scripts/pages/project_detail/sections/project_session_model.js";

const source = fs.readFileSync(
  "apps/portal/static/portal/js/proyecto_detalle.js",
  "utf8",
);
for (const [name, factory] of [
  ["aerIAState", initialAerAi],
  ["ixsIAState", initialIxsAi],
]) {
  test(`${name}: same initial fields as the previous implementation`, () => {
    const literal = source.match(new RegExp(`let ${name}=(\\{[^\\n]+\\});`))[1];
    const original = vm.runInNewContext(`(${literal})`);
    assert.deepEqual(factory(), JSON.parse(JSON.stringify(original)));
    const first = factory(),
      second = factory();
    for (const key of Object.keys(first)) {
      if (first[key] && typeof first[key] === "object")
        assert.notEqual(first[key], second[key]);
    }
  });
}
test("AER preserves object identity and cached results only for the same strict ID", () => {
  const state = initialAerAi("1");
  state.analisis = { saved: true };
  assert.equal(selectAerAi(state, { proyecto: { id: "1" } }), state);
  assert.deepEqual(
    selectAerAi(state, { proyecto: { id: 1 } }),
    initialAerAi(1),
  );
  assert.deepEqual(
    selectAerAi(state, { proyecto: { id: "2" } }),
    initialAerAi("2"),
  );
  const empty = initialAerAi();
  assert.notEqual(selectAerAi(empty, {}), empty);
  assert.deepEqual(selectAerAi(state, {}), initialAerAi());
});
test("IXS preserves its original string ID convention and resets project-specific sources", () => {
  const state = initialIxsAi("1");
  state.driveSelected.push("document");
  assert.equal(selectIxsAi(state, { proyecto: { id: 1 } }), state);
  assert.deepEqual(
    selectIxsAi(state, { proyecto: { id: "2" } }),
    initialIxsAi("2"),
  );
});
test("Clockify retains selected dates and cached entries on the same project", () => {
  const state = {
    proyectoId: "one",
    desde: "2026-01-01",
    registros: [1],
    requestId: 4,
  };
  assert.equal(
    selectClockify(state, "one", () => {
      throw Error("must not reset");
    }),
    state,
  );
});
test("Clockify switches to a fresh week and resets pending reads for another project", () => {
  const dates = { desde: "2026-10-19", hasta: "2026-10-25" };
  assert.deepEqual(
    selectClockify({ proyectoId: "one", registros: [1] }, "two", () => dates),
    {
      proyectoId: "two",
      registros: null,
      cargando: false,
      error: "",
      ...dates,
      requestId: 0,
    },
  );
});
test("AER outdated diagnostic keeps the previous backend and health requirements", () => {
  assert.equal(outdatedAer({}), true);
  assert.equal(outdatedAer({ backendVersion: "v3" }), false);
  assert.equal(
    outdatedAer({ plan: {}, kpis: { healthDimensiones: {} } }),
    false,
  );
  assert.equal(outdatedAer({ plan: {}, kpis: {} }), true);
});
