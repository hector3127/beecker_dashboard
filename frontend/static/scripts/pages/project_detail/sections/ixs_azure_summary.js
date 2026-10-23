import { azureSummary } from "./ixs_azure_summary_model.js";
import { renderAzureSummary } from "./ixs_azure_summary_view.js";

export function renderSummary(root, state) {
  renderAzureSummary(root, azureSummary(state));
}
