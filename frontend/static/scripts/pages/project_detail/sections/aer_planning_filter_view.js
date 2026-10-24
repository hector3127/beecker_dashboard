import { el, h, div, input, button } from "./aer_planning_dom.js";
import { PLAN_STATES } from "./aer_planning_model.js";
import { filterOptions, filterKeys } from "./aer_planning_filters_model.js";

export function closeFilter() {
  document.getElementById("aer-plan-filter-pop")?.remove();
}
let outsideInstalled = false;
export function installOutside() {
  if (outsideInstalled) return;
  outsideInstalled = true;
  document.addEventListener("click", (event) => {
    const pop = document.getElementById("aer-plan-filter-pop");
    if (
      pop &&
      !pop.contains(event.target) &&
      !event.target.closest(".aer-plan-filter-btn")
    )
      closeFilter();
  });
}
export function openFilter(event, field, rows, filters, handlers) {
  event.preventDefault();
  event.stopPropagation();
  closeFilter();
  const fields = [],
    controls = [];
  const add = (title, id, key, type = "text", props = {}) => {
    const node = input(filters[key] || "", { id, type, ...props });
    fields.push(el("label", { for: id }, title), node);
    controls.push([key, node]);
  };
  if (["tipo", "responsable", "estado"].includes(field)) {
    const values =
        field === "estado" ? PLAN_STATES : filterOptions(rows, field),
      id = "aer-hf-" + field;
    const node = el(
      "select",
      { id },
      el("option", { value: "" }, "Todos"),
      ...values.map((value) =>
        el("option", { value, selected: filters[field] === value }, value),
      ),
    );
    fields.push(el("label", { for: id }, "Mostrar"), node);
    controls.push([field, node]);
  } else if (field === "actividad")
    add("Buscar actividad", "aer-hf-actividad", "actividad", "text", {
      placeholder: "Escribe para buscar…",
    });
  else if (field === "compromiso" || field === "cierre") {
    const keys = filterKeys(field),
      prefix = field === "compromiso" ? "comp" : "cierre";
    add("Desde", `aer-hf-${prefix}-desde`, keys[0], "date");
    add("Hasta", `aer-hf-${prefix}-hasta`, keys[1], "date");
  }
  const name =
    field === "cierre"
      ? "Fecha de cierre"
      : field.charAt(0).toUpperCase() + field.slice(1);
  const pop = el(
    "div",
    { id: "aer-plan-filter-pop", class: "aer-plan-filter-pop" },
    h("h4", "", "Filtrar por " + name),
    ...fields,
    div(
      "actions",
      button("Borrar", () => handlers.clear(field, pop)),
      button(
        "Aplicar",
        () =>
          handlers.apply(
            Object.fromEntries(
              controls.map(([key, node]) => [key, node.value]),
            ),
            pop,
          ),
        "aer-btn primary",
      ),
    ),
  );
  document.body.append(pop);
  const r = event.currentTarget.getBoundingClientRect(),
    maxLeft = Math.max(8, window.innerWidth - 276);
  pop.style.left =
    Math.min(maxLeft, Math.max(8, r.left - 200 + r.width)) + "px";
  let top = Math.min(window.innerHeight - 300, r.bottom + 6);
  if (top < 8) top = 8;
  pop.style.top = top + "px";
  const first = pop.querySelector("input,select");
  if (first)
    setTimeout(() => {
      if (pop.isConnected) first.focus();
    }, 0);
  return pop;
}
