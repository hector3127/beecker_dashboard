import { taskNodes, raidNode, sourceError } from "./generic_sources_view.js";
import { raidModel } from "./generic_sources_model.js";

export function createGenericSources(data, documentRoot = document) {
  const requests = new WeakMap();
  const totalsIds = [
    "raid-proyecto-riesgos",
    "raid-proyecto-pendientes",
    "raid-proyecto-oportunidades",
  ];

  async function load(projectId, kind) {
    const id =
      kind === "raid"
        ? "riesgos-criticos-proyecto-azure"
        : "clockify-task-hours-proyecto";
    const target = documentRoot.getElementById(id);
    if (!target || !projectId) return;
    const request = {};
    requests.set(target, request);
    const totalNodes = totalsIds.map((key) => documentRoot.getElementById(key));
    const current = () =>
      documentRoot.getElementById(id) === target &&
      requests.get(target) === request;
    try {
      const result = await data[kind](projectId);
      if (!current()) return;
      if (!result || !result.ok) {
        const prefix =
          kind === "raid"
            ? "No se pudieron cargar riesgos de Azure: "
            : "No se pudieron cargar horas de Clockify: ";
        target.replaceChildren(
          sourceError(prefix + (result?.error || "Error desconocido")),
        );
        return;
      }
      if (kind === "tasks") target.replaceChildren(...taskNodes(result));
      else {
        target.replaceChildren(raidNode(result));
        raidModel(result).totals.forEach((value, index) => {
          const node = totalNodes[index];
          if (node && documentRoot.getElementById(totalsIds[index]) === node)
            node.textContent = value;
        });
      }
    } catch (error) {
      if (!current()) return;
      const prefix =
        kind === "raid"
          ? "Error cargando RAID de Azure: "
          : "Error cargando horas por task: ";
      target.replaceChildren(sourceError(prefix + (error?.message || error)));
    }
  }
  return { tasks: (id) => load(id, "tasks"), raid: (id) => load(id, "raid") };
}
