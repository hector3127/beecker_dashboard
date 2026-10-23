// @ts-check
// The server retains all project calculations; only presentation moves here.
import { watchLoadingMessages } from "#app/ui/portal-loading.js";

watchLoadingMessages();
document.querySelectorAll("[data-bar-width]").forEach((node) => {
  const bar = /** @type {HTMLElement} */ (node);
  bar.style.width = `${bar.dataset.barWidth}%`;
  bar.style.background = bar.dataset.barColor || "";
});
document.querySelectorAll("[data-marker-left]").forEach((node) => {
  const marker = /** @type {HTMLElement} */ (node);
  marker.style.left = `${marker.dataset.markerLeft}%`;
});
