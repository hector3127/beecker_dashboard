import { chartsModel } from "./generic_charts_model.js";
import { areaView, barsView } from "./generic_charts_view.js";
export function mountGenericCharts(data) {
  const model = chartsModel(data);
  document
    .getElementById("donut-area-ejecutivo")
    ?.replaceChildren(areaView(model));
  for (const [id, items, expandable] of [
    ["comparativo-recurso-mini", model.resources, true],
    ["comparativo-rol-mini", model.roles, false],
  ]) {
    const target = document.getElementById(id);
    if (!target) continue;
    const view = barsView(items, expandable, id);
    target.replaceChildren(view.root);
    if (view.link) {
      let expanded = false;
      view.link.addEventListener("click", (event) => {
        event.preventDefault();
        expanded = !expanded;
        view.hidden.style.display = expanded ? "block" : "none";
        view.link.textContent = expanded
          ? "Ver menos"
          : `Ver todos (${view.extra} más)`;
      });
    }
  }
}
