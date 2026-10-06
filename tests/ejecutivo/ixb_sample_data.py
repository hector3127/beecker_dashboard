"""Datos de ejemplo del resumen IXB/RaaS (compartidos con la prueba)."""

from datetime import datetime

from core.time_entries.models import TimeEntry
from core.utils.cell_types import CellValue

NOW = datetime(2026, 10, 2, 12, 0)

# Fechas como numero de serie de Sheets: 46023 = 2026-01-01.
PROJECT_ROWS = [
    {
        "ID_Proyecto": "RAS.001",
        "Nombre": "Robot Cobranza",
        "Cliente": "ACME",
        "Servicio": "RAAS",
        "Estado": "Development",
        "Budget_Hrs": 100,
    },
    {
        "ID_Proyecto": "RAS.001_CR1",
        "Nombre": "Robot Cobranza CR",
        "Cliente": "ACME",
        "Servicio": "RaaS",
        "Estado": "Development",
        "Budget_Hrs": 40,
    },
    {
        "ID_Proyecto": "IXB.002",
        "Nombre": "Portal",
        "Cliente": "Globex",
        "Servicio": "IXB",
        "Estado": "Cerrado",
        "Budget_Hrs": 80,
    },
    {
        "ID_Proyecto": "IXB.002_S2",
        "Nombre": "Portal S2",
        "Cliente": "Globex",
        "Servicio": "IXB",
        "Estado": "Development",
        "Budget_Hrs": 60,
    },
    {
        "ID_Proyecto": "POC.003",
        "Nombre": "Prueba",
        "Cliente": "Initech",
        "Servicio": "POC",
        "Estado": "Development",
        "Budget_Hrs": 20,
    },
    {
        "ID_Proyecto": "SAS.004",
        "Nombre": "",
        "Account": "Umbrella",
        "Servicio": "SAAS",
        "Estado": "Development",
        "Budget_Hrs": "50",
        "Scrum_Master": "Pedro",
    },
    {
        "ID_Proyecto": "AER.005",
        "Nombre": "Otro",
        "Cliente": "ACME",
        "Servicio": "AER",
        "Estado": "Development",
        "Budget_Hrs": 10,
    },
]

HISTORY_ROWS: list[dict[str, CellValue]] = [
    {
        "Project ID": "RAS.001_CR1",
        "Status": "Discovery EST",
        "Start": 46235,
        "Finish": 46254,
        "Delivery Manager": "",
    },
    {
        "Project ID": "RAS.001_CR1",
        "Status": "Discovery",
        "Start": 46235,
        "Finish": 46256,
        "Delivery Manager": "Laura",
    },
    {
        "Project ID": "RAS.001_CR1",
        "Status": "Development",
        "Start": 46257,
        "Finish": "",
        "Delivery Manager": "",
    },
    {
        "Project ID": "RAS.001",
        "Status": "Completed",
        "Start": 46200,
        "Finish": 46210,
        "Delivery Manager": "Otro",
    },
    {
        "Project ID": "IXB.002",
        "Status": "Discovery",
        "Start": 46143,
        "Finish": 46174,
        "Delivery Manager": "Mario",
    },
    {
        "Project ID": "IXB.002_S2",
        "Status": "Suspendido",
        "Start": 46280,
        "Finish": "",
        "Delivery Manager": "",
    },
    {
        "Project ID": "POC.003",
        "Status": "Completed",
        "Start": 46250,
        "Finish": 46260,
        "Delivery Manager": "Ana",
    },
    {
        "Project ID": "SAS.004",
        "Status": "Discovery EST",
        "Start": 46113,
        "Finish": 46130,
        "Delivery Manager": "Ana",
    },
    {
        "Project ID": "SAS.004",
        "Status": "Development EST",
        "Start": 46131,
        "Finish": 46400,
        "Delivery Manager": "",
    },
    {
        "Project ID": "SAS.004",
        "Status": "Discovery",
        "Start": 46113,
        "Finish": 46132,
        "Delivery Manager": "",
    },
    {
        "Project ID": "SAS.004",
        "Status": "Development OP",
        "Start": 46133,
        "Finish": "",
        "Delivery Manager": "",
    },
]

AZURE_PROJECTS = ["RAS.001", "IXB.002_Main", "Otro proyecto"]


def iteration(name, start=None, finish=None, children=()):
    attributes = {}
    if start:
        attributes["startDate"] = start
    if finish:
        attributes["finishDate"] = finish
    return {"name": name, "attributes": attributes, "children": list(children)}


ITERATION_TREES = {
    "RAS.001": iteration(
        "RAS.001",
        children=[
            iteration(
                "S1",
                children=[
                    iteration(
                        "Discovery",
                        "2026-01-05T00:00:00Z",
                        "2026-02-01T00:00:00Z",
                    ),
                    iteration(
                        "Deployment",
                        "2026-03-01T00:00:00Z",
                        "2026-04-01T00:00:00Z",
                    ),
                ],
            ),
            iteration(
                "CR1",
                children=[
                    iteration(
                        "Discovery",
                        "2026-08-01T00:00:00Z",
                        "2026-08-20T00:00:00Z",
                    ),
                    iteration(
                        "Development",
                        "2026-08-21T00:00:00Z",
                        "2026-10-15T00:00:00Z",
                    ),
                    iteration(
                        "Deployment",
                        "2026-10-01T00:00:00Z",
                        "2026-11-30T00:00:00Z",
                    ),
                ],
            ),
        ],
    ),
    "IXB.002_Main": iteration(
        "IXB.002_Main",
        children=[
            iteration(
                "General_S2_Discovery",
                "2026-05-01T00:00:00Z",
                "2026-06-01T00:00:00Z",
            ),
            iteration(
                "General_S2_Development",
                "2026-06-02T00:00:00Z",
                "2026-07-15T00:00:00Z",
            ),
            iteration(
                "General_S2_Deployment",
                "2026-07-16T00:00:00Z",
                "2026-09-20T00:00:00Z",
            ),
        ],
    ),
}


def work_item(item_id, item_type, state, path, title):
    return {
        "id": item_id,
        "fields": {
            "System.WorkItemType": item_type,
            "System.State": state,
            "System.IterationPath": path,
            "System.Title": title,
        },
    }


WORK_ITEMS = {
    "RAS.001": [
        work_item(1, "Task", "Closed", "RAS.001\\CR1\\Discovery", "T1"),
        work_item(2, "Task", "Active", "RAS.001\\CR1\\Development", "T2"),
        work_item(3, "Task", "Active", "RAS.001\\S1\\Development", "T3"),
        work_item(4, "Bug", "New", "RAS.001\\Deployment", "B1"),
        work_item(5, "Risk", "Active", "RAS.001", "Riesgo abierto"),
        work_item(6, "Risk", "Closed", "RAS.001", "Riesgo cerrado"),
        work_item(7, "Task", "Completed", "RAS.001", "General"),
    ],
    "IXB.002_Main": [
        work_item(
            8, "Task", "Active", "IXB.002_Main\\General_S2_Deployment", "T8"
        ),
    ],
}


def entry(entry_id, hours, billable=True, tags=(), task=""):
    return TimeEntry(
        entry_id=entry_id,
        project_id="",
        resource_name="Ana",
        entry_date=datetime(2026, 9, 1),
        duration_hours=hours,
        is_billable=billable,
        costing_rate=0.0,
        tags=tuple(tags),
        task_name=task,
    )


CLOCKIFY_ENTRIES = {
    "RAS.001_CR1": [
        entry("a", 10.5, tags=["CR1"]),
        entry("b", 4, tags=["S1"]),
        entry("c", 3, task="Desarrollo CR1"),
        entry("d", 2),
        entry("e", 8, billable=False),
        entry("a", 10.5, tags=["CR1"]),
    ],
    "IXB.002_S2": [entry("f", 70, tags=["S2 soporte"])],
}
