// Temporary original-only capture; run from repository root.
import fs from "node:fs";
import vm from "node:vm";
import path from "node:path";
import { createRequire } from "node:module";
import { createHash } from "node:crypto";
const require = createRequire(import.meta.url);
const domState = require(path.resolve("tests/frontend/dom_state.cjs"));
const { isLoadingMessage, begin, inspect } = require(
  path.resolve("tests/reference/static/portal/js/portal_loading.js"),
);
const messages = [
  "Consultando…",
  "Preparando corte del periodo…",
  "Cargando datos",
  "Guardando estado…",
  "Pendiente",
  "No disponible",
  "Sin presupuesto",
  "0",
  "31 costos pendientes",
  "Sin acuerdos registrados",
].map((value) => ({ value, expected: isLoadingMessage(value) }));
const target = domState(),
  first = begin(target),
  second = begin(target),
  overlap = [];
const record = () =>
  overlap.push({
    busy: target.getAttribute("aria-busy"),
    region: target.classList.contains("portal-loading-region"),
  });
record();
first();
record();
first();
record();
second();
record();
const message = {
  ...domState(),
  matches() {
    return true;
  },
  closest() {
    return null;
  },
  childElementCount: 0,
  textContent: "Consultando…",
};
inspect(message);
const skeleton = [message.classList.contains("portal-loading-message")];
message.textContent = "Pendiente";
inspect(message);
skeleton.push(message.classList.contains("portal-loading-message"));
const source = fs.readFileSync(
  "tests/reference/static/portal/js/return_navigation.js",
  "utf8",
);
const links = [];
function run(href, target, back = false) {
  const location = new URL(href),
    listeners = {};
  const link = {
    href: target,
    hasAttribute: (key) => back && key === "data-portal-back",
    classList: { contains: () => false },
  };
  vm.runInNewContext(source, {
    URL,
    URLSearchParams,
    location,
    document: {
      addEventListener: (name, fn) => (listeners[name] = fn),
      getElementById: () => null,
    },
  });
  listeners.click({ target: { closest: () => link } });
  links.push({ href, target, back, expected: link.href });
}
run(
  "http://localhost/ejecutiva/cuentas/?periodo=mes&anio=2026&mes=10&buscar=Heineken",
  "http://localhost/ejecutiva/costos/detalle/?nombre=Heineken",
);
run(
  "http://localhost/cuenta/a/?nombre=A&volver=%2Fejecutiva%2Fcuentas%2F",
  "http://localhost/ejecutiva/costos/detalle/?nombre=A",
);
run(
  "http://localhost/cuenta/heineken-mexico/?nombre=Heineken+Mexico&volver=%2F&periodo=mes&anio=2026&mes=10",
  "http://localhost/ejecutiva/oportunidades/?nombre=Heineken+Mexico",
);
run(
  "http://localhost/ejecutiva/costos/detalle/",
  "http://localhost/cuenta/a/?nombre=A&volver=%2Fejecutiva%2Fcuentas%2F",
  true,
);
run("http://localhost/", "https://other.test/cuenta/a/");
const location = new URL(
  "http://localhost/ejecutiva/cuentas/?periodo=anio&anio=2026&buscar=Heineken&clasificacion=pending",
);
const elements = Object.fromEntries(
  ["account-search", "account-filter"].map((id) => [
    id,
    {
      value: "",
      listeners: {},
      addEventListener(name, fn) {
        this.listeners[name] = fn;
      },
      dispatchEvent(event) {
        this.dispatched = event.type;
      },
    },
  ]),
);
let saved;
vm.runInNewContext(source, {
  URL,
  URLSearchParams,
  location,
  Event: class {
    constructor(type) {
      this.type = type;
    }
  },
  history: { state: null, replaceState: (state, title, url) => (saved = url) },
  document: { addEventListener() {}, getElementById: (id) => elements[id] },
});
const restored = {
  search: elements["account-search"].value,
  classification: elements["account-filter"].value,
};
elements["account-search"].value = "Otra cuenta";
elements["account-search"].listeners.input();
const css = fs
  .readFileSync(
    "tests/reference/static/portal/css/proyecto_detalle.css",
    "utf8",
  )
  .replaceAll("\r\n", "\n");
const captured = {
  loading: { messages, overlap, skeleton },
  navigation: {
    links,
    account: {
      href: location.href,
      restored,
      nextSearch: "Otra cuenta",
      saved,
    },
  },
  css: {
    sha256: createHash("sha256").update(css).digest("hex"),
    bytes: Buffer.byteLength(css, "utf8"),
    normalization: "CRLF to LF only",
  },
};
fs.writeFileSync(
  "tests/frontend/frozen/portal_auxiliary.json",
  JSON.stringify(captured, null, 2) + "\n",
);
