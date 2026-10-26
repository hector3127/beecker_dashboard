// Same range service and date presentation; late responses belong to their node.
import { shortDate } from "./generic_panels_model.js";

export function rangeText(result) {
  if (!result || !result.ok || !result.fechaInicio) return "";
  return `Clockify: ${shortDate(result.fechaInicio)} → ${shortDate(result.fechaFin)}`;
}

export function createClockifyRange(data, documentRoot = document) {
  const requests = new WeakMap();
  return {
    async load(projectId, elementId) {
      const target = documentRoot.getElementById(elementId);
      if (!target || !projectId) return;
      const request = {};
      requests.set(target, request);
      target.textContent = "Consultando rango…";
      const current = () =>
        documentRoot.getElementById(elementId) === target &&
        requests.get(target) === request;
      try {
        const result = await data.clockifyRange(projectId);
        if (current()) target.textContent = rangeText(result);
      } catch {
        if (current()) target.textContent = "";
      }
    },
  };
}
