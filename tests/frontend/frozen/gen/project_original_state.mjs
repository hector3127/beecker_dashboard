// Temporary original-only harness. Never imported by normal tests.
import vm from "node:vm";
export function originalState(source, extra = {}) {
  const NativeDate = Date;
  const scope = {
    window: {},
    Date: class extends NativeDate {
      constructor(...args) {
        super(...(args.length ? args : ["2026-10-23T18:00:00Z"]));
      }
    },
    ...extra,
  };
  vm.createContext(scope);
  const declarations = source.match(
    /^  (?:var|const) \w+ = window\.beeProjectState[^\n]+/gm,
  );
  vm.runInContext(declarations.join("\n"), scope);
  const bindings = declarations.map((line) => {
    const m = line.match(
      /(?:var|const) (\w+) = window\.beeProjectState \? window\.beeProjectState\.(\w+)/,
    );
    return { name: m[1], key: m[2] };
  });
  const store = {};
  for (const { name, key } of bindings)
    Object.defineProperty(store, key, {
      enumerable: true,
      get: () => vm.runInContext(name, scope),
      set: (value) => {
        scope.__write = value;
        vm.runInContext(`${name}=__write`, scope);
        delete scope.__write;
      },
    });
  return { scope, store, bindings, declarations };
}
export function load(source, scope, names) {
  for (const name of names) {
    const line = source
      .split("\n")
      .find((line) => line.startsWith(`  function ${name}(`));
    const code = line.trim().endsWith("}")
      ? line
      : source.match(new RegExp(`  function ${name}\\([\\s\\S]*?\\n  \\}`))[0];
    vm.runInContext(code, scope);
  }
}
export const plain = (value) => JSON.parse(JSON.stringify(value));
export function describe(value, path = "callback") {
  if (typeof value === "function") return { $callback: value.__name || path };
  if (Array.isArray(value))
    return value.map((item, i) => describe(item, `${path}.${i}`));
  if (value && typeof value === "object")
    return Object.fromEntries(
      Object.entries(value).map(([k, v]) => [k, describe(v, `${path}.${k}`)]),
    );
  return value;
}
export function stub(scope, calls, names) {
  for (const name of names) {
    const fn = (...args) => calls.push([name, ...args]);
    fn.__name = name;
    scope[name] = fn;
  }
}
