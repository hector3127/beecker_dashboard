import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";

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
  assert.deepEqual(
    fs.readFileSync("frontend/static/styles/pages/project_detail_base.css"),
    fs.readFileSync("apps/portal/static/portal/css/proyecto_detalle.css"),
  );
});
