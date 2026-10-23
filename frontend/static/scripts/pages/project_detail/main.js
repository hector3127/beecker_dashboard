// @ts-check
// Transitional entry: keep the existing renderers until each tab is migrated.
import { createProjectData } from "./data.js";
import { renderAerExecutive } from "./sections/aer_executive.js";
import { el } from "#app/lib/dom.js";
import { watchLoadingMessages } from "#app/ui/portal-loading.js";

const root = document.getElementById("view-container");
const entry = document.querySelector("[data-project-detail-entry]");

/** @param {string} src @returns {Promise<void>} */
function loadScript(src) {
  return new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = src;
    script.onload = () => resolve();
    script.onerror = () => {
      script.remove();
      reject(new Error("No se pudo cargar la interfaz del proyecto."));
    };
    document.head.append(script);
  });
}

let started = false;
async function start() {
  if (started || !entry || !root) return;
  started = true;
  try {
    // Preserve the old actions and their CSRF protection during the tab rollout.
    const shim = entry.getAttribute("data-rpc-shim");
    const renderer = entry.getAttribute("data-legacy-script");
    if (!shim || !renderer) throw new Error("Falta la entrada del proyecto.");
    await loadScript(shim);
    Object.assign(window, {
      beeProjectData: createProjectData(),
      beeProjectExecutive: renderAerExecutive,
    });
    await loadScript(renderer);
  } catch {
    started = false;
    const retry = el("button", { type: "button", class: "btn" }, "Reintentar");
    retry.addEventListener("click", start);
    root.replaceChildren(
      el(
        "div",
        { class: "card" },
        el(
          "p",
          { role: "status" },
          "No se pudo cargar la interfaz del proyecto.",
        ),
        retry,
      ),
    );
  }
}

watchLoadingMessages();
start();
