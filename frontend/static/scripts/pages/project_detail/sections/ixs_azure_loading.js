import { el } from "#app/lib/dom.js";

const sections = [
  "ixs-azure-stale",
  "ixs-azure-health",
  "ixs-azure-table",
  "ixs-az84-person",
  "ixs-az84-stage",
];

// Keep the original loading/error boxes, using text nodes for source errors.
export function azureMessage(root, text, sourceFailure = false) {
  const ids = sourceFailure
    ? [
        "ixs-azure-kpis",
        ...sections,
        "ixs-azure-by-assignee",
        "ixs-azure-dates",
        "ixs-azure-status-summary",
      ]
    : sections;
  for (const id of ids) {
    root
      .querySelector("#" + id)
      ?.replaceChildren(el("div", { class: "ixs-azure-empty" }, text));
  }
}
