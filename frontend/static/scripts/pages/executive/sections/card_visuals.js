// @ts-check
// controller: executive/sections/card_visuals. Original data, ordering and interactions are preserved.
import { gauge, monthly } from "./card_visuals_view.js";
/**
 * @param {Record<string, any>} model
 */
export function renderCardVisuals(model) {
  monthly("executive-revenue", model.monthly?.months || []);
  monthly("executive-margin", model.monthly?.months || [], true);
  gauge("executive-collections", model.revenue?.collections_percent);
  gauge("executive-ops-advance", model.operations?.advance);
  gauge("executive-ops-facturability", model.operations?.facturability);
}
