// @ts-check
// Register modular views; the compatibility script still supplies shared bindings.
import { createProjectData } from "./data.js";
import { createProjectShell } from "./sections/project_shell.js";
import { createProjectTabs } from "./sections/project_tabs.js";
import { createProjectSession } from "./sections/project_session.js";
import { createProjectEntry } from "./sections/project_entry.js";
import { createIxsSupport } from "./sections/ixs_support.js";
import {
  createProjectState,
  bindProjectState,
} from "./sections/project_state.js";
import { actionsModel } from "./sections/actions_model.js";
import { createActionsController } from "./sections/actions.js";
import { createAerPlanning } from "./sections/aer_planning.js";
import { createAerEffort } from "./sections/aer_effort.js";
import { createAerRisks } from "./sections/aer_risks.js";
import { createAerResources } from "./sections/aer_resources.js";
import { createAerAiSources } from "./sections/aer_ai_sources.js";
import { createAerAiPresentation } from "./sections/aer_ai_presentation.js";
import { createAerAiActions } from "./sections/aer_ai_actions.js";
import * as aerAiModel from "./sections/aer_ai_model.js";
import * as aerPlanningModel from "./sections/aer_planning_model.js";
import { createAiSources } from "./sections/ixs_ai_sources.js";
import * as aiModel from "./sections/ixs_ai_model.js";
import { createAiController } from "./sections/ixs_ai_controller.js";
import { createClientActionsLoader } from "./sections/ixs_client_actions.js";
import { renderAiPanels } from "./sections/ixs_ai_panels_view.js";
import {
  renderAi,
  renderDocuments,
  renderTranscripts,
} from "./sections/ixs_ai_view.js";
import { createAzureController } from "./sections/ixs_azure.js";
import { createAzureGroupsController } from "./sections/ixs_azure_groups.js";
import { renderSummary } from "./sections/ixs_azure_summary.js";
import { createAzureTab } from "./sections/ixs_azure_tab.js";
import { renderAerExecutive } from "./sections/aer_executive.js";
import { createEffortController } from "./sections/ixs_effort.js";
import { createResourcesController } from "./sections/ixs_resources.js";
import { createCommuniqueController } from "./sections/communique.js";
import { prependDataNotice } from "./sections/data_notice.js";
import { createClientController } from "./sections/client.js";
import { createCommunicationController } from "./sections/bee_com.js";
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
    const azureGroups = createAzureGroupsController();
    Object.assign(window, {
      beeProjectData: data,
      beeProjectActionsModel: actionsModel,
      beeProjectActions: createActionsController(data),
      beeAerPlanning: createAerPlanning(data),
      beeProjectShell: createProjectShell(data),
      beeAerEffort: createAerEffort(data),
      beeAerRisks: createAerRisks(data),
      beeAerResources: createAerResources(data),
      beeAerAiSources: createAerAiSources(data),
      beeAerAiPresentation: createAerAiPresentation(),
      beeAerAiActions: createAerAiActions(data),
      beeAerAiModel: aerAiModel,
      beeAerPlanningModel: aerPlanningModel,
      beeIxsAiSources: createAiSources(data),
      beeIxsAiModel: aiModel,
      beeIxsAiController: createAiController(data),
      beeIxsClientActions: createClientActionsLoader(data),
      beeIxsAiPanels: renderAiPanels,
      beeIxsAiView: {
        render: renderAi,
        documents: renderDocuments,
        transcripts: renderTranscripts,
      },
      beeIxsAzure: createAzureController(data),
      beeIxsAzureGroups: azureGroups,
      beeIxsAzureSummary: renderSummary,
      beeIxsAzureTab: createAzureTab(data, azureGroups),
      beeIxsEffort: createEffortController(data),
      beeIxsResources: createResourcesController(data),
      beeIxsPlanningEditor: createPlanningEditor(data),
      beeProjectCommunique: communique,
      beeProjectClient: createClientController(data),
      beeIxsCommunication: createCommunicationController(data),
      beeIxsRaid: createRaidController(data, createRaidCreator(data)),
      beeProjectMilestones: createMilestoneController(data),
      beeIxsPlanning: createPlanningController(data),
      beeProjectExecutive: (target, project, ...rest) => {
        renderAerExecutive(target, project, ...rest);
        prependDataNotice(target, project.proyecto);
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
    window.beeProjectTabs = createProjectTabs(window, renderAerExecutive);
    window.beeProjectSession = createProjectSession(data, window);
    window.beeProjectEntry = createProjectEntry(data);
    window.beeIxsSupport = createIxsSupport(data, window);
    window.beeProjectState ||= createProjectState();
    bindProjectState(window, window.beeProjectState);
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
