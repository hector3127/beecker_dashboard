// Temporary original-only capture.
import fs from "node:fs";
import { originalState, plain } from "./project_original_state.mjs";
const source = fs.readFileSync(
  "tests/reference/static/portal/js/proyecto_detalle.js",
  "utf8",
);
const { store, bindings } = originalState(source);
const defaults = bindings.map(({ name, key }) => ({
  name,
  key,
  expected: plain(store[key]),
}));
fs.writeFileSync(
  "tests/frontend/frozen/project_state.json",
  JSON.stringify({ defaults }, null, 2) + "\n",
);
