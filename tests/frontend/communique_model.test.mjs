import test from "node:test";
import assert from "node:assert/strict";
import { kindsFor, missingField, payload, previewBlocks } from "../../frontend/static/scripts/pages/project_detail/sections/communique_model.js";

const text = (blocks) =>
  blocks
    .map((b) =>
      b
        .map((s) => (typeof s === "string" ? s : s.b ?? s.ph ?? s.a ?? (s.li ? s.li.map((x) => x.b ?? x).join("") : "")))
        .join(""),
    )
    .join("\n");
const ctx = { project: "MCC.015_S3", hasFiles: false, hour: 9, today: "2026-10-23" };

test("IXB has four kinds and AER only extension and close", () => {
  assert.deepEqual(kindsFor("ixb"), ["extension", "suspension", "reanudacion", "cierre_ixb"]);
  assert.deepEqual(kindsFor("aer"), ["extension", "cierre_aer"]);
});
test("suspension preview matches the server template", () => {
  const out = text(previewBlocks("suspension", { reason: "Sin accesos.", stage: "Development", resumeDate: "2026-11-02", condition: "la entrega de accesos" }, ctx));
  assert.match(out, /^Buenos días ROC,\nInformo la suspensión temporal del proyecto MCC\.015_S3, debido a:\nSin accesos\./);
  assert.match(out, /La fecha tentativa de reanudación es 02\/11\/2026, siempre que se confirme la entrega de accesos\./);
});
test("AER close says today only for today's date", () => {
  assert.match(text(previewBlocks("cierre_aer", { closeDate: "2026-10-23" }, ctx)), /el día de hoy - 23\/10\/2026 - el cierre/);
  assert.match(text(previewBlocks("cierre_aer", { closeDate: "2026-10-22", description: "las mejoras" }, ctx)), /el día 22\/10\/2026 el cierre de este proyecto MCC\.015_S3 - afiliado a las mejoras\./);
});
test("validation names the missing data and the IXB close needs the MCO", () => {
  assert.equal(missingField("reanudacion", {}, "X", 0), "Falta la fecha de reanudación.");
  assert.equal(missingField("cierre_ixb", { closeDate: "2026-10-15" }, "X", 0), "Adjunta la MCO como archivo o pon su enlace.");
  assert.equal(missingField("cierre_ixb", { closeDate: "2026-10-15" }, "X", 1), "");
  assert.equal(missingField("extension", { stage: "Discovery", currentDate: "2026-01-01", newDate: "2026-01-02", reason: "x" }, "X", 0), "Falta el link del roadmap.");
});
test("payload uses the server field names", () => {
  const fields = Object.fromEntries(payload("cierre_aer", { closeDate: "2026-10-23", description: "las mejoras", link: "https://a.b" }, " AER.1 ", "19abc"));
  assert.deepEqual(fields, { kind: "cierre_aer", project: "AER.1", threadId: "19abc", closeDate: "2026-10-23", description: "a las mejoras", link: "https://a.b" });
  assert.equal(Object.fromEntries(payload("extension", { link: "https://r" }, "X", "t")).roadmapLink, "https://r");
});
