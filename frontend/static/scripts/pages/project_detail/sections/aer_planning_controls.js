import {
  emptyFilters,
  initialRange,
  filterKeys,
  rowMatches,
} from "./aer_planning_filters_model.js";
import {
  closeFilter,
  openFilter,
  installOutside,
} from "./aer_planning_filter_view.js";

const rows = () => [
  ...document.querySelectorAll("#aer-plan-table-body tr[data-plan-row]"),
];
const visibleChecks = () =>
  rows()
    .filter((row) => row.style.display !== "none")
    .map((row) => row.querySelector(".aer-plan-row-check"))
    .filter(Boolean);
function syncAll() {
  const all = document.getElementById("aer-plan-select-all");
  if (!all) return;
  const checks = visibleChecks(),
    selected = checks.filter((node) => node.checked);
  all.checked = checks.length > 0 && selected.length === checks.length;
  all.indeterminate = selected.length > 0 && selected.length < checks.length;
}
export function applyFilters(filters) {
  const items = rows();
  let visible = 0;
  items.forEach((row) => {
    const show = rowMatches(row.dataset || {}, filters);
    row.style.display = show ? "" : "none";
    if (show) visible++;
  });
  const count = document.getElementById("aer-plan-filter-count");
  if (count) count.textContent = `${visible} de ${items.length}`;
  syncAll();
}
export function selection() {
  const selected = [...document.querySelectorAll(".aer-plan-row-check")].filter(
    (node) => node.checked,
  );
  const count = document.getElementById("aer-plan-selected-count"),
    button = document.getElementById("aer-plan-delete-selected");
  if (count)
    count.textContent = `${selected.length} seleccionada${selected.length === 1 ? "" : "s"}`;
  if (button) button.disabled = selected.length === 0;
  syncAll();
}
export function toggleAll(checked) {
  visibleChecks().forEach((node) => {
    node.checked = !!checked;
  });
  selection();
}
export function createPlanningControls(env) {
  installOutside();
  const paint = () => {
    if (env.current() && env.active()) env.paint();
  };
  const setFilters = (patch) => env.setFilters({ ...env.filters(), ...patch });
  return {
    initialize() {
      env.setRange(initialRange(env.range()));
    },
    rangeChange(field, value) {
      const range = initialRange(env.range());
      if (field === "desde" || field === "hasta")
        range[field] = value || range[field];
      env.setRange(range);
      paint();
    },
    filterSet(field, value) {
      setFilters({ [field]: String(value == null ? "" : value) });
      applyFilters(env.filters());
    },
    clearFilters() {
      env.setFilters(emptyFilters());
      paint();
    },
    toggleAll,
    selection,
    applyFilters() {
      applyFilters(env.filters());
    },
    closeFilter,
    openFilter(event, field) {
      return openFilter(
        event,
        field,
        env.dashboard.plan?.filas || [],
        env.filters(),
        {
          clear: (key, pop) => {
            if (!env.current()) return;
            setFilters(Object.fromEntries(filterKeys(key).map((k) => [k, ""])));
            pop.remove();
            paint();
          },
          apply: (values, pop) => {
            if (!env.current()) return;
            setFilters(values);
            pop.remove();
            paint();
          },
        },
      );
    },
    applyHeader(field) {
      const prefix = field === "compromiso" ? "comp" : field;
      const keys = filterKeys(field),
        patch = {};
      keys.forEach((key, i) => {
        const id =
          keys.length === 1
            ? `aer-hf-${field}`
            : `aer-hf-${prefix}-${i ? "hasta" : "desde"}`;
        patch[key] = document.getElementById(id)?.value || "";
      });
      setFilters(patch);
      closeFilter();
      paint();
    },
    clearHeader(field) {
      setFilters(Object.fromEntries(filterKeys(field).map((key) => [key, ""])));
      closeFilter();
      paint();
    },
  };
}
