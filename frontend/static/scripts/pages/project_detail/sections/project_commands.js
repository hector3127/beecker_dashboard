import { createIxsTools } from "./project_ixs_tools.js";

// Public compatibility names delegate to modular controllers, never to RPC.
// Existing callers can keep their entry points while normal UI events use
// the controllers directly. No rendering/form logic is duplicated here.
export function bindProjectCommands(views, store) {
  const aer = () => views.beeAerRuntime;
  const ixs = () => views.beeIxsRuntime;
  const tools = createIxsTools(store, views, views.beeIxsSupport);
  const plan = () => views.beeAerPlanning.bind(aer().planningContext());
  const controls = () => views.beeAerPlanning.controls(aer().planningContext());
  const resources = () => views.beeAerResources.bind(aer().resourcesContext());
  const effort = () => views.beeAerEffort.bind(aer().effortContext());
  const commands = {
    loadDashboard: () => views.beeProjectEntryRuntime.load(),
    showError: (error) => views.beeProjectEntry.serverError(error),
    projectEntryContext: () => views.beeProjectEntryRuntime.context(),
    projectSessionContext: () =>
      views.beeProjectContexts.session({
        styles: tools.styles,
        render: {
          aer: () => aer().mount(),
          ixs: () => ixs().mount(),
          aerTab: () => aer().dispatch(),
          ai: () => ixs().paintAi(),
        },
        aiLoads: Object.fromEntries(
          ["sources", "history", "drive"].map((source) => [
            source,
            () => views.beeIxsAdapters.load(source, () => ixs().paintAi()),
          ]),
        ),
      }),
    abrirModalHito: (id) =>
      views.beeProjectMilestones.open(id, store.milestones, () =>
        views.beeProjectEntryRuntime.load(),
      ),
    abrirModalRiesgo: (id) => views.beeGenericRisk.open(id),
    _pintarRangoClockifyProyecto: (...args) =>
      views.beeProjectClockifyRange.load(...args),
    cargarRaidProyectoEjecutivoAzure: (id) => views.beeGenericSources.raid(id),
    cargarHorasTasksProyectoClockify: (id) => views.beeGenericSources.tasks(id),
    renderDashboardAERTYMProyecto: (data) => aer().initialize(data),
    renderDashboardIXBSaaSRaaS: (data) => ixs().initialize(data),
    renderDashboardEjecutivoProyecto: (data) =>
      views.beeGenericExecutive.mount(data),
    aerCambiarTab: (tab) => aer().select(tab),
    ixsCambiarTab: (tab) => ixs().select(tab),
    aerRecargarProyecto: () => aer().refresh(),
    ixsRecargarProyecto: () => ixs().refresh(),
    _aerRenderTab: () => aer().dispatch(),
    _ixsRenderTab: () => ixs().dispatch(),
    _aerRenderShell: () => aer().mount(),
    _ixsRenderShell: () => ixs().mount(),
    aerCerrarModal: () => views.beeProjectFeedback.close(),
    aerCerrarModalWide: () => views.beeProjectFeedback.close(true),
    _aerStartSaving: (...args) => views.beeProjectFeedback.saving(...args),
    _aerPrimaryModalBtn: () => views.beeProjectFeedback.primary(),
    _aerToast: (...args) => views.beeProjectFeedback.toast(...args),
    ixsAbrirVistaAnterior: () => views.beeProjectPrevious.open(),
    ixsVolverEjecutivoNuevo: (id) => views.beeProjectPrevious.back(id),
    ixsIAAbrir: () => ixs().openAi(),
    ixsIAPintar: () => ixs().paintAi(),
    ixsCargarClienteAcciones: () => ixs().loadClientActions(),
    aerAbrirEvaluacion: (uid) => resources().open(uid),
    aerAbrirRiesgo: (uid) => aer().risks().open(uid),
    aerLimpiarDuplicadosRiesgos: () => aer().risks().clean(),
    aerAbrirAccion: (uid) => aer().actions().open(uid),
    aerIAAbrirNuevaAccionParte: (...args) =>
      aer()
        .actions()
        .openPart(...args),
    aerAbrirRegistrosClockify: () => effort().openRecords(),
    aerConsultarRegistrosClockify: () => effort().query(),
    ixsCerrarExtension: () => views.beeProjectCommunique.close(),
    ixsAbrirExtension: () => tools.communique(),
    ixsAbrirPlanEditor: (...args) => tools.editPlanning(...args),
    _ixsCargarEstadosRecursos: () =>
      views.beeIxsSupport.resources(
        views.beeIxsAdapters.support(() => views.beeProjectEntryRuntime.load()),
      ),
    ixsIAContexto: () => views.beeIxsAdapters.context(),
    ixsIASnapshot: () => views.beeIxsAdapters.snapshot(),
    ixsIACambios: () => views.beeIxsAdapters.changes(),
    ixsIACapacidad: () => views.beeIxsAdapters.capacity(),
  };
  const bind = (mapping, get) => {
    for (const [name, method] of Object.entries(mapping))
      commands[name] = (...args) => get()[method](...args);
  };
  bind(
    {
      aerAbrirPlan: "openPlan",
      aerAbrirVacacion: "openVacation",
      aerAbrirImportPlan: "openImport",
      aerEliminarVacacion: "removeVacation",
      aerEliminarPlanesSeleccionados: "removeSelected",
      aerGuardarEstadoModal: "modalState",
    },
    plan,
  );
  bind(
    {
      aerCambiarRangoPlan: "rangeChange",
      _aerPlanFilterSet: "filterSet",
      aerLimpiarFiltrosPlan: "clearFilters",
      aerAplicarFiltrosPlan: "applyFilters",
      aerTogglePlanAll: "toggleAll",
      aerActualizarSeleccionPlan: "selection",
      aerAbrirFiltroCabecera: "openFilter",
      aerCerrarFiltroCabecera: "closeFilter",
      aerAplicarFiltroCabecera: "applyHeader",
      aerLimpiarFiltroCabecera: "clearHeader",
    },
    controls,
  );
  bind(
    {
      aerIACorreo: "mail",
      aerIAAbrirMinuta: "openMinute",
      aerIAAbrirConfigMinutas: "config",
      aerIAVerMinuta: "minute",
      aerIAVerResumenEjecutivo: "summary",
      aerIAOcultarArchivos: "hideFiles",
      aerIAAlternarHistorial: "history",
    },
    () => aer().presentation(),
  );
  bind({ aerIAAnalizar: "analyze" }, () => aer().aiActions());
  bind(
    {
      ixsIAAnalizar: "analyze",
      ixsIAPreguntar: "ask",
      ixsIAMemoriaGuardar: "memory",
      ixsIAEvidencia: "evidence",
      ixsIAVerMinuta: "minute",
      ixsIACrearMinuta: "createMinute",
      ixsIAReporteBorrador: "report",
      ixsIAConfigurarDrive: "configureDrive",
      ixsIAPrepararMinutaDrive: "prepareDriveMinute",
      ixsIABorradorAccion: "action",
      ixsIARAID: "raid",
    },
    () => ixs().aiActions(),
  );
  for (const [name, source] of Object.entries({
    aerIACargarAnalisis: "analysis",
    aerIACargarMinutas: "minutes",
    aerIACargarConfigMinutas: "config",
    aerIACargarResumenEjecutivo: "summary",
    aerIACargarAccionesPartes: "parts",
  }))
    commands[name] = (...args) => aer().load(source, ...args);
  for (const [name, source] of Object.entries({
    ixsIACargarFuentes: "sources",
    ixsIACargarHistoria: "history",
    ixsIACargarDrive: "drive",
  }))
    commands[name] = () =>
      views.beeIxsAdapters.load(source, () => ixs().paintAi());
  return Object.assign(views, commands);
}
