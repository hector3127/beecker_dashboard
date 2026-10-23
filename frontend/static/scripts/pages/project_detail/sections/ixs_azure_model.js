// Same panel shape as the former loader; no KPI or business rule changes.
export function azurePanel(result, projectId, requestId) {
  return {
    projectId,
    requestId,
    sinPAT: false,
    error: "",
    notice: result.aviso || "",
    items: Array.isArray(result.items) ? result.items : [],
    allItems: Array.isArray(result.allItems) ? result.allItems : [],
    stale: Array.isArray(result.stale) ? result.stale : [],
  };
}
