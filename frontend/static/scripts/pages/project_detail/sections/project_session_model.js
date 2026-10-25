import { currentWeek } from "./ixs_effort_model.js";
export function initialAerAi(id = "") {
  return {
    id,
    analisis: null,
    minutas: null,
    resumenEjecutivo: null,
    respuestaChatResumen: null,
    resumenConsultado: false,
    cargandoResumen: false,
    accionesPartes: null,
    cargandoPartes: false,
    cargando: false,
    cargandoAnalisis: false,
    analisisConsultado: false,
    config: null,
    archivos: null,
    seleccion: [],
    mostrarArchivos: false,
    archivosOcultos: false,
    historialCompleto: false,
    errorBusqueda: "",
  };
}
export function initialIxsAi(id = "") {
  return {
    id,
    azure: null,
    plan: null,
    resources: null,
    clockify: null,
    cliente: null,
    raid: null,
    memoria: null,
    minutas: [],
    driveConfig: null,
    driveFiles: [],
    driveSelected: [],
    driveError: "",
    driveLoading: false,
    analisis: null,
    error: "",
    loading: false,
    question: "",
    respuesta: "",
    sourceErrors: {},
    request: 0,
  };
}
export function selectAerAi(previous, project) {
  const id = (project.proyecto || {}).id;
  return previous.id !== id ? initialAerAi(id || "") : previous;
}
export function selectIxsAi(previous, project) {
  const id = String(project.proyecto.id);
  return previous.id !== id ? initialIxsAi(id) : previous;
}
export function selectClockify(previous, id, week = currentWeek) {
  if (previous.proyectoId === id) return previous;
  return {
    proyectoId: id,
    registros: null,
    cargando: false,
    error: "",
    ...week(),
    requestId: 0,
  };
}
export const outdatedAer = (data) =>
  !data.backendVersion &&
  (!data.plan || !data.kpis || !data.kpis.healthDimensiones);
