// @ts-check
// Transitional entry: keep the existing renderers until each tab is migrated.
import { createProjectData } from "./data.js";
import { createAzureController } from "./sections/ixs_azure.js";
import { createAzureGroupsController } from "./sections/ixs_azure_groups.js";
import { renderSummary } from "./sections/ixs_azure_summary.js";
import { renderAerExecutive } from "./sections/aer_executive.js";
import { createEffortController } from "./sections/ixs_effort.js";
import { createResourcesController } from "./sections/ixs_resources.js";
import { createCommuniqueController } from "./sections/communique.js";
import { prependCommuniqueActions } from "./sections/communique_actions.js";
import { prependDataNotice } from "./sections/data_notice.js";
import { createRaidCreator } from "./sections/raid_create.js";
import { createRaidController } from "./sections/raid.js";
import { createMilestoneController } from "./sections/milestones.js";
import { createPlanningEditor } from "./sections/ixs_planning_editor.js";
import { createPlanningController } from "./sections/ixs_planning.js";
import {
  mountIxsExecutive,
  updateTimeline,
  resourceTable,
} from "./sections/ixs_executive.js";
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
    const data = createProjectData();
    const communique = createCommuniqueController();
    Object.assign(window, {
      beeProjectData: data,
      beeIxsAzure: createAzureController(data),
      beeIxsAzureGroups: createAzureGroupsController(),
      beeIxsAzureSummary: renderSummary,
      beeIxsEffort: createEffortController(data),
      beeIxsResources: createResourcesController(data),
      beeIxsPlanningEditor: createPlanningEditor(data),
      beeProjectCommunique: communique,
      beeIxsRaid: createRaidController(data, createRaidCreator(data)),
      beeProjectMilestones: createMilestoneController(data),
      beeIxsPlanning: createPlanningController(data),
      beeProjectExecutive: (target, project, ...rest) => {
        renderAerExecutive(target, project, ...rest);
        prependDataNotice(target, project.proyecto);
        prependCommuniqueActions(target, project.proyecto, communique);
      },
      beeIxsExecutive: {
        mount: (target, project, lifecycle) => {
          mountIxsExecutive(target, project, data, lifecycle);
          prependDataNotice(target, project.proyecto);
        },
        updateTimeline,
        resourceTable,
      },
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
