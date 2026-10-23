"""Quien puede llamar cada funcion de /api/rpc/."""

from typing import Any

from django.core.exceptions import PermissionDenied
from django.http import Http404

from apps.access.checks import resolve

"""BKD.140.008 - Politica del RPC
/api/rpc/ conserva las funciones del frontend original. Cada una declara aqui
la capacidad que pide; las de una cuenta ademas verifican el alcance de la
persona. Con alcance limitado solo se permiten las funciones de cuenta: las
demas trabajan con proyectos o con el equipo completo. Una funcion sin
politica se rechaza, asi una funcion nueva no queda abierta por olvido.
"""

OPERATIONS = "view_operations"
EDIT = "edit_operations"
SETTINGS = "manage_integrations"

# Funciones de una cuenta: el primer argumento es su nombre.
ACCOUNT_READ = {
    "obtenerVistaCuentaBeecker",
    "obtenerConsumosMPBCuenta",
    "obtenerOportunidadesCuentaBeecker",
}
ACCOUNT_WRITE = {"beeCuentaGuardarOportunidad"}

INTEGRATION_SETTINGS = {
    "cambiarProyectoActivoAzureDevOps",
    "desconectarAzureDevOps",
    "diagnosticoClockify",
    "diagnosticoClockifyCompleto",
    "guardarApiKeyClaude",
    "guardarApiKeyClockify",
    "guardarConfigAzureDevOps",
    "guardarConfigCarpetaMinutasAER",
    "guardarPromptPersonalizadoClaude",
    "guardarVinculoProyectoClockify",
    "guardarWorkspaceClockify",
    "ixsIADriveConfigGuardar",
    "ixsIADriveConfigLeer",
    "ixsIADriveConfigQuitar",
    "ixsRaidGuardarPrompt",
    "limpiarValidacionesIAClockify",
    "listarProyectosAzureDevOps",
    "listarProyectosGuardadosAzureDevOps",
    "listarWorkspacesClockify",
    "obtenerConfigAzureDevOps",
    "obtenerConfigCarpetaMinutasAER",
    "obtenerConfigClaude",
    "obtenerConfigClockify",
    "probarConexionAzureDevOps",
}
WRITES = {
    "actualizarAjusteGarantia",
    "actualizarAjusteUAT",
    "actualizarCampoAccionAER",
    "actualizarCampoAccionParteAER",
    "actualizarDesdeUltimaMinuta",
    "actualizarEsfuerzoPlaneacionAER",
    "actualizarEstadoCierrePlaneacionAER",
    "actualizarEstadoPendienteDaily",
    "agregarAjusteGarantia",
    "agregarAjusteUAT",
    "agregarComentarioWorkItem",
    "agregarPendienteDaily",
    "agregarRiesgoManual",
    "analizarProyectoClaudeAER",
    "beeComGuardar",
    "crearWorkItemRiesgoAzure",
    "editarHitoAdicional",
    "eliminarAccionAER",
    "eliminarAccionParteAER",
    "eliminarAjusteGarantia",
    "eliminarAjusteUAT",
    "eliminarAreaRegla",
    "eliminarContactoAER",
    "eliminarDocumentoClienteAER",
    "eliminarEvaluacionAER",
    "eliminarHitoAdicional",
    "eliminarLotePlaneacionAER",
    "eliminarPendienteDaily",
    "eliminarPlaneacionAER",
    "eliminarRiesgoAER",
    "eliminarVacacionAER",
    "generarBorradorMinutaClaudeAER",
    "generarBorradorMinutaDesdeCarpetaClaudeAER",
    "generarResumenEjecutivoClaudeAER",
    "generarSugerenciaRiesgoConClaude",
    "guardarAccionAER",
    "guardarAccionParteAER",
    "guardarAreaRegla",
    "guardarCampoAvanceWorkItem",
    "guardarClienteInfoAER",
    "guardarContactoAER",
    "guardarDocumentoClienteAER",
    "guardarEvaluacionAER",
    "guardarGobiernoClienteAER",
    "guardarHitoAdicional",
    "guardarHitosAdicionalesLote",
    "guardarLotePlaneacionAER",
    "guardarMinutaIAProyectoAER",
    "guardarPlaneacionAER",
    "guardarRiesgoAER",
    "guardarVacacionAER",
    "ixsActualizarCampoAccion",
    "ixsActualizarCampoAccionParte",
    "ixsClienteAccionesActualizar",
    "ixsClienteAccionesActualizarParte",
    "ixsClienteAccionesEliminar",
    "ixsClienteAccionesGobierno",
    "ixsClienteAccionesGuardar",
    "ixsClienteAccionesLimpiarDuplicados",
    "ixsEliminarAccion",
    "ixsEliminarAccionParte",
    "ixsEliminarContacto",
    "ixsEliminarDocumentoCliente",
    "ixsGuardarAccion",
    "ixsGuardarAccionParte",
    "ixsGuardarClienteInfo",
    "ixsGuardarContacto",
    "ixsGuardarDocumentoCliente",
    "ixsGuardarGobiernoCliente",
    "ixsIAAnalizar",
    "ixsIADriveGenerarMinuta",
    "ixsIAMemoriaActualizar",
    "ixsIAMinutaGuardar",
    "ixsIAPreguntar",
    "ixsLimpiarDuplicadosAcciones",
    "ixsPlanEliminar",
    "ixsPlanGuardar",
    "ixsRaidCrearRegistro",
    "ixsRaidSugerirClaude",
    "ixsRecursosGuardar",
    "limpiarDuplicadosAccionesAER",
    "limpiarDuplicadosRiesgosAER",
    "marcarCierrePlaneacionAER",
    "preguntarClaudeProyectoAER",
    "redactarCorreoClaudeAER",
}
READS = {
    "beeComListar",
    "buscarIteraciones",
    "buscarMinutasCarpetaAER",
    "buscarUsuariosAzureDevOps",
    "buscarWorkItemsParaRelacionar",
    "capacidadInstaladaBase",
    "capacidadInstaladaDatosProyecto",
    "diagnosticarConexionClockifyProyecto",
    "diagnosticarHorasClockifyProyecto",
    "getAccionesAERProyecto",
    "getDashboardAERTYMProyecto",
    "getDashboardData",
    "getDashboardEjecutivoProyecto",
    "getDetallePersona",
    "getDetalleProyectoCompleto",
    "getFiltrosDisponibles",
    "getMinutasViewData",
    "getPersonasConHoras",
    "getProyectosConHoras",
    "getProyectosConMinutas",
    "getRegistrosClockifyAERRango",
    "getRegistrosClockifyProyecto",
    "getResumenRecursos",
    "getRiesgosAERProyecto",
    "gseGuardarResultadoCache",
    "gseLeerResultadoCache",
    "gseObtenerAnoBase",
    "gseObtenerAreas",
    "gseObtenerIDsClockify",
    "gseObtenerLoteBase",
    "gseObtenerMes",
    "inspeccionarCamposWorkItem",
    "ixsClienteAccionesLeer",
    "ixsGetAccionesProyecto",
    "ixsIAAnalisisLeer",
    "ixsIADriveLeerDocumento",
    "ixsIADriveListar",
    "ixsIAMemoriaLeer",
    "ixsIAMinutasLeer",
    "ixsListarAccionesPartes",
    "ixsPlanLeer",
    "ixsRaidAltaOpciones",
    "ixsRaidCamposTipo",
    "ixsRaidListarProyecto",
    "ixsRaidObtenerPrompt",
    "ixsRecursosLeer",
    "listarAccionesPartesAER",
    "listarMinutasIAProyectoAER",
    "listarProyectosClockify",
    "listarSprintsProyecto",
    "obtenerAjustesGarantia",
    "obtenerAjustesUAT",
    "obtenerAreasReglas",
    "obtenerConsumosResumenAERTYMMPB",
    "obtenerEtapasHistoricoAIProyecto",
    "obtenerFormularioRiesgoAzure",
    "obtenerOportunidadesAzureDevOps",
    "obtenerPanelAzureProyectoIXS",
    "obtenerPendientesDaily",
    "obtenerPromptMinutaDefectoAER",
    "obtenerProyectosAsignadosPersona",
    "obtenerRaidProyectoEjecutivoAzure",
    "obtenerRangoClockifyProyecto",
    "obtenerRegistrosMalRegistrados",
    "obtenerResumenAERTYMMPB",
    "obtenerResumenEjecutivoParaDaily",
    "obtenerResumenIXBRaaS",
    "obtenerResumenTasksTagsClockifyProyecto",
    "obtenerRiesgosAzureDevOps",
    "obtenerTiposHitosExistentes",
    "obtenerTopRiesgosPortafolioAzure",
    "obtenerUltimoAnalisisProyectoAER",
    "obtenerUltimoResumenEjecutivoAER",
    "obtenerWorkItemsPendientes",
    "obtenerWorkItemsPorTipo",
    "obtenerWorkItemsSinSeguimiento",
    "obtenerWorkItemsToBeYCR",
}

POLICY: dict[str, tuple[str, ...]] = {
    **dict.fromkeys(READS, (OPERATIONS,)),
    **dict.fromkeys(WRITES, (EDIT,)),
    **dict.fromkeys(INTEGRATION_SETTINGS, (SETTINGS,)),
    **dict.fromkeys(ACCOUNT_READ, (OPERATIONS, "view_agreements")),
    **dict.fromkeys(ACCOUNT_WRITE, (EDIT,)),
}


def authorize_rpc(request: Any, name: str, args: list[object]) -> None:
    """Rechaza la llamada si la persona no puede hacerla.

    Con los accesos apagados no cambia nada. Una cuenta fuera del alcance no
    existe (404); lo demas es 403.
    """
    access = resolve(request)
    if not access.enforced:
        return
    if not request.user.is_authenticated:
        raise PermissionDenied
    needed = POLICY.get(name)
    if needed is None or not any(access.can(code) for code in needed):
        raise PermissionDenied
    if name in ACCOUNT_READ | ACCOUNT_WRITE:
        if not access.scope.allows_account(args[0] if args else None):
            raise Http404("No existe esa cuenta.")
    elif not access.scope.unrestricted:
        raise PermissionDenied
