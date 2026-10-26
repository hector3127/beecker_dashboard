import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import { riskPayload } from "../../frontend/static/scripts/pages/project_detail/sections/generic_risk_model.js";

test("manual risk trims only description and preserves original field values", () => {
  const values = {
    descripcion: "  Entrega\npendiente  ",
    impacto: "Medio",
    probabilidad: "Media",
    responsable: " Ana ",
  };
  assert.deepEqual(riskPayload(values), {
    ...values,
    descripcion: "Entrega\npendiente",
  });
  assert.equal(values.descripcion, "  Entrega\npendiente  ");
  assert.equal(riskPayload({ ...values, descripcion: "  " }).descripcion, "");
});

function setup() {
  const dialogs = [],
    calls = [];
  let current = "A",
    reloads = 0,
    resolve;
  const context = {
    riskPayload,
    document: {
      body: {
        append(node) {
          node.isConnected = true;
        },
      },
    },
    riskDialog(handlers) {
      const dialog = {
        handlers,
        overlay: {
          isConnected: false,
          remove() {
            this.isConnected = false;
          },
        },
        fields: {
          descripcion: " Risk ",
          impacto: "Alto",
          probabilidad: "Alta",
          responsable: " Ana ",
        },
        values() {
          return this.fields;
        },
        busy(value) {
          this.saving = value;
        },
        message(text) {
          this.error = text;
        },
      };
      dialogs.push(dialog);
      return dialog;
    },
  };
  const source = fs
    .readFileSync(
      "frontend/static/scripts/pages/project_detail/sections/generic_risk.js",
      "utf8",
    )
    .replace(/import[^;]+;/g, "")
    .replace("export function", "function");
  vm.runInNewContext(source, context);
  const controller = context.createGenericRisk(
    {
      saveManualRisk(...args) {
        calls.push(args);
        return new Promise((r) => (resolve = r));
      },
    },
    {
      current: (id) => id === current,
      reload() {
        reloads++;
      },
    },
  );
  return {
    controller,
    dialogs,
    calls,
    finish: (value) => resolve(value),
    change: (id) => (current = id),
    reloads: () => reloads,
  };
}

test("save validates, prevents duplicate requests and reloads once after success", async () => {
  const s = setup();
  s.controller.open("A");
  const dialog = s.dialogs[0];
  dialog.fields.descripcion = " ";
  await s.controller.save();
  assert.equal(dialog.error, "Falta la descripción del riesgo.");
  assert.equal(s.calls.length, 0);
  dialog.fields.descripcion = " Risk ";
  const pending = s.controller.save();
  await s.controller.save();
  assert.equal(s.calls.length, 1);
  assert.equal(dialog.saving, true);
  assert.equal(s.calls[0][0], "A");
  assert.equal(s.calls[0][1].responsable, " Ana ");
  s.finish({ ok: true });
  await pending;
  assert.equal(s.reloads(), 1);
  assert.equal(dialog.overlay.isConnected, false);
});

test("a closed or different project form ignores delayed success", async () => {
  for (const change of ["close", "project"]) {
    const s = setup();
    s.controller.open("A");
    const work = s.controller.save();
    if (change === "close") {
      s.controller.close();
      s.controller.open("A");
    } else s.change("B");
    s.finish({ ok: true });
    await work;
    assert.equal(s.reloads(), 0);
    if (change === "close")
      assert.equal(s.dialogs[1].overlay.isConnected, true);
  }
});

test("logical failure preserves form and enables retry", async () => {
  const s = setup();
  s.controller.open("A");
  const dialog = s.dialogs[0];
  const work = s.controller.save();
  s.finish({ ok: false, error: "Denied" });
  await work;
  assert.equal(dialog.error, "Error al guardar: Denied");
  assert.equal(dialog.saving, false);
  assert.equal(dialog.overlay.isConnected, true);
  assert.equal(s.reloads(), 0);
  const retry = s.controller.save();
  s.finish({ ok: true });
  await retry;
  assert.equal(s.reloads(), 1);
});
