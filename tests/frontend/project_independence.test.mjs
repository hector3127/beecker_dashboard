import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { createHash } from "node:crypto";

const base = "frontend/static/scripts/pages/project_detail";
function localGraph(file, visited = new Map()) {
  if (visited.has(file)) return visited;
  const source = fs.readFileSync(file, "utf8");
  visited.set(file, source);
  for (const match of source.matchAll(
    /(?:from\s+|import\s*)["'](\.[^"']+)["']/g,
  ))
    localGraph(
      path.normalize(path.join(path.dirname(file), match[1])),
      visited,
    );
  return visited;
}

test("the active project dependency graph has no legacy loader, shim or RPC transport", () => {
  const graph = localGraph(path.join(base, "main.js"));
  assert.ok(graph.size > 100, "Audit the full module graph, not only main");
  for (const [file, source] of graph) {
    assert.doesNotMatch(
      source,
      /proyecto_detalle\.js|gas_shim\.js|\/api\/rpc\/|google\.script\.run/,
      file,
    );
    assert.doesNotMatch(
      source,
      /createProjectScriptLoader|data-legacy-script|data-rpc-shim/,
      file,
    );
  }
  const template = fs.readFileSync(
    "frontend/templates/pages/project_detail.html",
    "utf8",
  );
  assert.doesNotMatch(
    template,
    /portal\/js|gas_shim|data-legacy-script|data-rpc-shim|portal\/css\/proyecto_detalle/,
  );
});

test("shared project CSS is relocated verbatim to preserve the reference appearance", () => {
  const frozen = JSON.parse(
    fs.readFileSync(
      new URL("./frozen/portal_auxiliary.json", import.meta.url),
      "utf8",
    ),
  ).css;
  const css = fs
    .readFileSync(
      "frontend/static/styles/pages/project_detail_base.css",
      "utf8",
    )
    .replaceAll("\r\n", "\n");
  assert.equal(Buffer.byteLength(css, "utf8"), frozen.bytes);
  assert.equal(createHash("sha256").update(css).digest("hex"), frozen.sha256);
});
