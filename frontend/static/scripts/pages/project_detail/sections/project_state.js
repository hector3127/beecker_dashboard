import { initialAerAi, initialIxsAi } from "./project_session_model.js";

export function createProjectState() {
  return {
    aer: null,
    aerTab: "ejecutivo",
    ixs: null,
    ixsTab: "resumen",
    aerAi: initialAerAi(),
    ixsAi: initialIxsAi(),
    clockify: {
      proyectoId: "",
      registros: null,
      cargando: false,
      error: "",
      desde: "",
      hasta: "",
      requestId: 0,
    },
    metadata: {},
    request: 0,
    milestones: [],
    projectId: null,
    clientCache: {},
    aerPlanningRange: { desde: "", hasta: "" },
    aerPlanningFilters: {
      tipo: "",
      actividad: "",
      responsable: "",
      compromisoDesde: "",
      compromisoHasta: "",
      estado: "",
      cierreDesde: "",
      cierreHasta: "",
    },
    aerRecords: {
      desde: "",
      hasta: "",
      registros: null,
      total: 0,
      cargando: false,
    },
    aerResourceSelection: "",
    ixsPlanning: {
      proyectoId: "",
      vacaciones: [],
      compromisos: [],
      cargando: false,
      error: "",
      requestId: 0,
    },
    ixsPlanningAzure: {
      proyectoId: "",
      items: [],
      allItems: [],
      cargando: false,
      error: "",
      requestId: 0,
    },
    ixsAzure: {
      projectId: "",
      items: [],
      allItems: [],
      stale: [],
      requestId: 0,
      sinPAT: false,
      error: "",
      notice: "",
    },
  };
}

// Temporary bindings for the compatibility script. Values belong to this store;
// existing callbacks keep their names until their remaining contexts are extracted.
export function bindProjectState(target, state) {
  const bindings = {
    aerDashboardData: "aer",
    aerTabActual: "aerTab",
    ixsProyectoActual: "ixs",
    ixsTabActual: "ixsTab",
    aerIAState: "aerAi",
    ixsIAState: "ixsAi",
    ixsClockifyState: "clockify",
    mapaMetaProyectosDashboard: "metadata",
    dashboardRequestSeq: "request",
    hitosAdicionalesActuales: "milestones",
    idProyectoActualGlobal: "projectId",
    aerPlanFiltroMes: "aerPlanningRange",
    aerPlanTableFilters: "aerPlanningFilters",
    aerClockifyFiltro: "aerRecords",
    aerEvalRecursoSeleccionado: "aerResourceSelection",
    ixsPlanState: "ixsPlanning",
    ixsPlanAzureState: "ixsPlanningAzure",
    ixsAzureState: "ixsAzure",
  };
  for (const [name, key] of Object.entries(bindings)) {
    Object.defineProperty(target, name, {
      configurable: true,
      enumerable: true,
      get: () => state[key],
      set: (value) => {
        state[key] = value;
      },
    });
  }
}
