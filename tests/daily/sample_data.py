"""Datos de prueba del panel Daily.

expected_results.json es la salida de DailyPanelService.gs con estos
datos, una organizacion de Azure DevOps simulada y la fecha
2026-10-02 12:00 (America/Mexico_City).
"""

from core.utils.cell_types import CellValue

ORGANIZATION = "beecker"
PAT = "pat-secreto-1234"
PROJECT = "RAS.001"


def work_item(item_id, item_type, title, state, changed, **extra):
    """Work item como lo regresa la API de Azure DevOps."""
    fields = {
        "System.Id": item_id,
        "System.Title": title,
        "System.WorkItemType": item_type,
        "System.State": state,
        "System.ChangedDate": changed,
        "System.CreatedDate": "2026-08-01T10:00:00.12Z",
        "System.IterationPath": f"{PROJECT}\\General_S1",
    }
    fields.update(extra)
    return {"id": item_id, "fields": fields}


ANA = {"displayName": "Ana Pérez", "uniqueName": "ana@beecker.ai"}

WORK_ITEMS = {
    "101": work_item(
        101,
        "To Be",
        "REQ-01 Alta de usuarios",
        "Active",
        "2026-09-20T15:04:05.123Z",
        **{"System.AssignedTo": ANA, "System.Tags": "S1; QA"},
    ),
    "102": work_item(
        102,
        "Change Request",
        "CR-02 Ajuste de reporte",
        "New",
        "2026-10-01T09:00:00Z",
        **{"Microsoft.VSTS.Scheduling.DueDate": "2026-10-15T00:00:00Z"},
    ),
    "201": work_item(
        201,
        "Risk",
        "Riesgo de ambiente",
        "Active",
        "2026-09-10T08:30:00Z",
        **{
            "System.AssignedTo": {"uniqueName": "luis@beecker.ai"},
            "Microsoft.VSTS.Common.Severity": "2 - Medium",
        },
    ),
    "301": work_item(
        301,
        "Opportunity",
        "Automatizar cierre",
        "Proposed",
        "2026-09-25T12:00:00Z",
        **{"Microsoft.VSTS.Common.Priority": 2},
    ),
    "401": work_item(
        401,
        "Bug",
        "Error en login",
        "Active",
        "2026-09-30T12:00:00Z",
        **{"Custom.Puntos": 5.0, "Custom.Lista": [1, 2.5, "x"]},
    ),
}

# Consulta WIQL -> IDs, segun el texto de la consulta.
WIQL_ROUTES = [
    ("IN ('To Be','Change Request','Risk','Opportunity')", [201, 101]),
    ("IN ('To Be','Change Request')", [102, 101]),
    ("[System.WorkItemType] = 'Risk'", [201]),
    ("[System.WorkItemType] = 'Opportunity'", [301]),
    ("[System.WorkItemType] = 'Bug'", [401]),
    ("[System.WorkItemType] = 'Nada'", []),
    ("NOT IN", [102, 201, 101, 301]),
    ("' ORDER BY", [101, 201, 102]),
]

RISK_FIELDS = [
    {
        "referenceName": "Microsoft.VSTS.Common.Severity",
        "name": "Severity",
        "allowedValues": ["1 - Critical", "2 - Medium"],
    },
    {
        "referenceName": "Microsoft.VSTS.Common.Priority",
        "name": "Priority",
        "allowedValues": [1, 2, 3],
    },
    {"referenceName": "Custom.PlanMitigacion", "name": "Plan de mitigación"},
    {"referenceName": "Custom.Notas", "name": "Mitigation notes"},
    {"referenceName": "Custom.Triggers", "name": "Triggers"},
    {
        "referenceName": "Custom.Categoria",
        "name": "Categoría",
        "allowedValues": ["Tecnico", "Negocio"],
    },
    {"referenceName": "Custom.Fuente", "name": "Fuente"},
    {"referenceName": "Custom.Seguimiento", "name": "Fecha de seguimiento"},
    {"referenceName": "System.Title", "name": "Title"},
]

ITERATION_TREE = {
    "name": "RAS.001",
    "children": [
        {
            "name": "General_S1",
            "attributes": {
                "startDate": "2026-08-01T00:00:00Z",
                "finishDate": "2026-08-31T00:00:00Z",
            },
        },
        {
            "name": "General_S2",
            "children": [
                {
                    "name": "Sprint 1",
                    "attributes": {"startDate": "2026-09-01T00:00:00.5Z"},
                },
            ],
        },
    ],
}

AZURE_PROJECTS = [
    {"id": "p2", "name": "ras.001"},
    {"id": "p1", "name": "RAS.001"},
    {"id": "p3", "name": "Árbol"},
    {"id": "p4", "name": "ERR401"},
    {"id": "p5", "name": "ERR500"},
    {"id": "p6", "name": "DETAIL500"},
    {"id": "p7", "name": "WRITE403"},
]

SHEETS: dict[str, list[list[CellValue]]] = {
    "Proyectos": [
        ["ID_Proyecto", "Nombre", "Estado"],
        ["RAS.001_S2", "RaaS S2", "Development"],
        ["RAS.001_S10", "RaaS S10", "Cerrado"],
        ["RAS.001", "", "Cancelado"],
        ["RAS.001_CR", "RaaS CR", "Discovery"],
        ["AMK.008", "AMK", "Development"],
    ],
    "WorkItems_Avance": [
        [
            "ID_WorkItem",
            "Proyecto",
            "Dev_Pct",
            "QA_Listo",
            "TTProd_Listo",
            "Fecha_Limite_Dev",
            "Demo",
        ],
        [102, "RAS.001", "60", True, "TRUE", 46315, "Demo previa"],
    ],
}

# (funcion del original, argumentos).
OPERATIONS = [
    ("obtenerConfigAzureDevOps", []),
    ("probarConexionAzureDevOps", []),
    ("listarProyectosAzureDevOps", ["beecker", ""]),
    ("listarProyectosAzureDevOps", ["nope", ""]),
    ("listarProyectosAzureDevOps", ["", ""]),
    ("listarProyectosGuardadosAzureDevOps", []),
    ("obtenerWorkItemsPendientes", [False]),
    ("obtenerWorkItemsPendientes", [False]),
    ("obtenerWorkItemsPendientes", [True]),
    ("obtenerRiesgosAzureDevOps", [False]),
    ("obtenerOportunidadesAzureDevOps", [False]),
    ("obtenerWorkItemsToBeYCR", [False]),
    ("obtenerWorkItemsSinSeguimiento", [7]),
    ("obtenerWorkItemsSinSeguimiento", [None]),
    ("obtenerWorkItemsSinSeguimiento", ["3"]),
    ("inspeccionarCamposWorkItem", ["Bug"]),
    ("inspeccionarCamposWorkItem", ["Nada"]),
    ("guardarCampoAvanceWorkItem", [101, "devConstruido", 150]),
    ("guardarCampoAvanceWorkItem", [101, "qa", True]),
    ("guardarCampoAvanceWorkItem", [102, "demo", "Demo 1"]),
    ("guardarCampoAvanceWorkItem", [102, "devConstruido", "45.5"]),
    ("guardarCampoAvanceWorkItem", [101, "otro", 1]),
    ("obtenerWorkItemsToBeYCR", [False]),
    ("obtenerFormularioRiesgoAzure", []),
    ("buscarIteraciones", [""]),
    ("buscarIteraciones", ["s2"]),
    ("buscarUsuariosAzureDevOps", ["ANA"]),
    ("buscarUsuariosAzureDevOps", [None]),
    ("buscarWorkItemsParaRelacionar", ["10"]),
    ("buscarWorkItemsParaRelacionar", ["riesgo"]),
    (
        "crearWorkItemRiesgoAzure",
        [
            {
                "titulo": "  Riesgo nuevo ",
                "descripcion": "Linea 1\nLinea 2",
                "responsable": "ana@beecker.ai",
                "nivel": "2 - Medium",
                "prioridad": 2,
                "planMitigacion": "Plan A",
                "triggers": "Disparador",
                "contingencyPlan": "",
                "categoria": "Tecnico",
                "fuenteRiesgo": "Cliente",
                "fechaSeguimiento": "",
                "relatedWorkItemId": " 101 ",
                "iterationPath": "RAS.001\\General_S2",
            },
        ],
    ),
    ("crearWorkItemRiesgoAzure", [{"titulo": "  "}]),
    (
        "crearWorkItemRiesgoAzure",
        [{"titulo": "Otro", "relatedWorkItemId": "x1"}],
    ),
    ("agregarComentarioWorkItem", [101, "  Revisado con el cliente "]),
    ("agregarComentarioWorkItem", [101, "   "]),
    ("cambiarProyectoActivoAzureDevOps", ["WRITE403"]),
    ("crearWorkItemRiesgoAzure", [{"titulo": "Sin permiso"}]),
    ("agregarComentarioWorkItem", [5, "Hola"]),
    ("cambiarProyectoActivoAzureDevOps", ["RAS.001"]),
    ("cambiarProyectoActivoAzureDevOps", ["  "]),
    ("cambiarProyectoActivoAzureDevOps", ["ERR401"]),
    ("obtenerWorkItemsPendientes", [True]),
    ("obtenerWorkItemsToBeYCR", [True]),
    ("cambiarProyectoActivoAzureDevOps", ["ERR500"]),
    ("obtenerWorkItemsPendientes", [True]),
    ("obtenerWorkItemsSinSeguimiento", [7]),
    ("inspeccionarCamposWorkItem", ["Bug"]),
    ("cambiarProyectoActivoAzureDevOps", ["DETAIL500"]),
    ("obtenerWorkItemsPendientes", [True]),
    ("obtenerRiesgosAzureDevOps", [True]),
    ("obtenerWorkItemsToBeYCR", [True]),
    ("cambiarProyectoActivoAzureDevOps", ["NOPE"]),
    ("probarConexionAzureDevOps", []),
    ("guardarConfigAzureDevOps", ["beecker", "RAS.001", PAT]),
    ("obtenerConfigAzureDevOps", []),
    ("guardarConfigAzureDevOps", ["", "RAS.001", PAT]),
    ("guardarConfigAzureDevOps", ["beecker", "", PAT]),
    ("listarSprintsProyecto", ["RAS.001_S2"]),
    ("listarSprintsProyecto", ["NADA"]),
    ("listarSprintsProyecto", [""]),
    (
        "agregarPendienteDaily",
        ["  Revisar ambiente ", "RAS.001", " Ana ", "Alta", None],
    ),
    (
        "agregarPendienteDaily",
        ["Llamar cliente", "AMK.008", "", "Urgente", None],
    ),
    ("agregarPendienteDaily", ["   ", "AMK.008", "", "Alta", None]),
    ("obtenerPendientesDaily", [None]),
    ("actualizarEstadoPendienteDaily", ["PND-1790964000001", "Completado"]),
    ("actualizarEstadoPendienteDaily", ["PND-1790964000001", "Otro"]),
    ("actualizarEstadoPendienteDaily", ["NOEXISTE", "Abierto"]),
    ("obtenerPendientesDaily", ["Todos los proyectos"]),
    ("obtenerPendientesDaily", ["AMK.008"]),
    ("agregarAjusteUAT", ["Ajuste uno", "RAS.001", 150]),
    ("agregarAjusteUAT", ["", "RAS.001", 10]),
    ("agregarAjusteUAT", ["Ajuste dos", "AMK.008", "40"]),
    ("obtenerAjustesUAT", [None]),
    ("actualizarAjusteUAT", ["ADJ-1790964000003", 55, True]),
    ("actualizarAjusteUAT", ["ADJ-1790964000004", None, False]),
    ("actualizarAjusteUAT", ["NO", 1, True]),
    ("eliminarAjusteUAT", ["ADJ-1790964000004"]),
    ("eliminarAjusteUAT", ["NO"]),
    ("obtenerAjustesUAT", ["RAS.001"]),
]
