"""Datos de prueba de Capacidad instalada.

Los resultados esperados se obtuvieron ejecutando el
CapacidadInstaladaService.gs original con estos mismos datos.
"""

from core.utils.cell_types import CellValue

# 46023 = 2026-01-01 y 46387 = 2026-12-31 como numero de serie de Sheets.
SHEETS: dict[str, list[list[CellValue]]] = {
    "Bandas/rol": [
        ["Bandas por rol"],
        [
            "Nombre",
            "ROL",
            "Tipo recurso",
            "Banda",
            "Enero 2026",
            "octubre 2026",
        ],
        ["Ana Pérez", "QA", "Empleado", "B2", "B1", "B3"],
        ["Luis Gómez", "DEV", "Becario", "B1", "", "Baja"],
        ["María López", "PM", "", "B4", "NA", "B4"],
        ["Pedro Ruiz", "DEV", "Residente", "B2", "B2", "B2"],
        ["Sofía Díaz", "", "Empleado", "", "", ""],
        ["", "x"],
        ["Carlos Ñúñez", "QA"],
    ],
    "Recursos": [
        [
            "Proyecto",
            "Nombre del recurso",
            "Conceptos",
            "Tipo recurso",
            "Iteration Path",
            "Horas diarias",
            "Horas Estimadas",
            "Estado recurso",
            "Nombre Proyecto",
        ],
        ["RAS.001_S2", "Ana Pérez", "Proyecto", "", "", "8", "160", "Activo"],
        ["RAS.001_S2", "ana perez", "", "", "", 4, "1,5", "", ""],
        ["AER.010", "María López", "", "", "", "abc", -3, "Inactivo", ""],
        ["", "Luis Gómez", "Vacaciones", "", "", 8, 0, "", ""],
        [
            "GPO.007",
            "Nuevo Recurso",
            "Interno",
            "Becario",
            "Proj\\Iter",
            "",
            " ",
            "baja",
            "",
        ],
        ["XYZ.1", "Ana Pérez", "Pre Ventas", "", "", 2.5, 0, "", "Manual"],
        ["", "", "", "", "", "", "", "", ""],
        ["TYM.002", "Pedro Ruiz", "Laboratorio Beecker"],
        ["NOP.001", "Sofía Díaz", "Concepto raro", "", "", "0x10", "1e1"],
    ],
    "Proyectos": [
        ["ID_Proyecto", "Nombre_Proyecto"],
        ["RAS.001_S2", "Robot RAS"],
        ["GPO.007", ""],
        ["NOP.001", "Sin Azure"],
    ],
    "Historico_Proyectos": [
        ["Project ID", "Status", "Delivery Manager"],
        ["RAS.001_S2", "Discovery", "Juan DM"],
        ["GPO.007", "Discovery", "Laura DM"],
        ["GPO.007", "Development", "Otra DM"],
    ],
    "MPB": [
        ["Reporte MPB"],
        [
            "CLIENTE",
            "ID",
            "NOMBRE",
            "SERVICE",
            "INICIO",
            "FIN",
            "Delivery Manager",
        ],
        ["C1", "AER.010", "Soporte AER", "AER", 46023, "2026-12-31", "Mgr A"],
        ["C2", "TYM.002", "", "T & M", "1/15/2026", 46387, ""],
        ["C3", "IXB.001", "IXB", "IXB", 46023, 46387, "Mgr C"],
    ],
}

MPB_DATE_COLUMNS = (4, 5)

AZURE_PROJECTS = ["RAS.001", "GPO.007_S1", "BAD.001", "ONE.001"]


def iteration(name, start="", finish="", children=()):
    """Crea un nodo del arbol de iteraciones de Azure."""
    attributes = {}

    if start:
        attributes["startDate"] = f"{start}T00:00:00Z"

    if finish:
        attributes["finishDate"] = f"{finish}T00:00:00Z"

    return {"name": name, "attributes": attributes, "children": list(children)}


AZURE_TREES = {
    "RAS.001": iteration(
        "RAS.001",
        children=[
            iteration(
                "General_S1",
                children=[
                    iteration("Discovery", "2026-02-01", "2026-03-15"),
                    iteration("Deployment", "2026-03-16", "2026-05-30"),
                ],
            ),
            iteration(
                "General_S2",
                children=[
                    iteration("Discovery", "2026-09-10", "2026-09-30"),
                    iteration("Development", "2026-10-01", "2026-10-20"),
                    iteration("Deployment", "2026-10-21", "2026-11-30"),
                    iteration("Sin fechas", "2026-12-01", "2026-11-01"),
                ],
            ),
        ],
    ),
    "GPO.007_S1": iteration(
        "GPO.007_S1",
        children=[
            iteration(
                "Proj",
                children=[
                    iteration("Iter", "2026-09-20", "2026-10-05"),
                    iteration("Otra", "2026-11-01", "2026-11-30"),
                ],
            ),
            iteration("Proj Iter 2", "2025-01-01", "2025-02-01"),
        ],
    ),
    "BAD.001": iteration("BAD.001", children=[iteration("Discovery")]),
    "ONE.001": iteration(
        "ONE.001",
        children=[iteration("General_S2", "2026-10-01", "2026-10-31")],
    ),
}

CLOCKIFY = {
    "AER.010": [
        {"recurso": "María López", "fecha": "2026-10-01", "duracion": 2.5},
        {"recurso": "Maria Lopez", "fecha": "2026-10-01", "duracion": 1.25},
        {"recurso": "Ana Pérez", "fecha": "2026-10-03", "duracion": 0.1},
        {"recurso": "Ana Pérez", "fecha": "2026-10-03", "duracion": 0.2},
        {"recurso": "Ana Pérez", "fecha": "2026-09-30", "duracion": 9},
    ],
    "RAS.001": [
        {
            "recurso": "Ana Pérez",
            "fecha": "2026-10-02",
            "duracion": 3,
            "task": "Desarrollo S2",
        },
        {
            "recurso": "Ana Pérez",
            "fecha": "2026-10-02",
            "duracion": 1,
            "task": "S1 soporte",
        },
        {
            "recurso": "Ana Pérez",
            "fecha": "2026-10-05",
            "duracion": 2,
            "task": "Sin task",
        },
        {
            "recurso": "Pedro Ruiz",
            "fecha": "2026-10-06",
            "duracion": 4,
            "task": "S2/CR1",
        },
        {
            "recurso": "Pedro Ruiz",
            "fecha": "2026-10-07",
            "duracion": 1.5,
            "task": "Reunion",
        },
        {
            "recurso": "Pedro Ruiz",
            "fecha": "2026-10-08",
            "duracion": 0.5,
            "task": "",
        },
        {
            "recurso": "Pedro Ruiz",
            "fecha": "2026-11-02",
            "duracion": 8,
            "task": "S2",
        },
    ],
    "GPO.007": [
        {"recurso": "Nuevo Recurso", "fecha": "2026-10-04", "duracion": 6},
        {"recurso": "", "fecha": "2026-10-05", "duracion": 1},
    ],
    "ONE.001": [],
}

BASE_SCENARIOS = ["2026-10", "2026-01", "2026-03", "", "2026-13"]

PROJECT_SCENARIOS = [
    ("AER.010", "", "2026-10"),
    ("TYM.002", "", "2025-12"),
    ("TYM.999", "", "2026-10"),
    ("RAS.001_S2", "", "2026-10"),
    ("RAS.001", "", "2026-03"),
    ("GPO.007", "Proj\\Iter", "2026-10"),
    ("GPO.007", "GPO.007_S1\\Proj\\Iter", "2026-10"),
    ("GPO.007", "gpo 007 s1 proj", "2026-09"),
    ("GPO.007", "", "2026-10"),
    ("GPO.007", "Missing\\Path", "2026-10"),
    ("NOP.001", "", "2026-10"),
    ("RAS.001_CR1", "", "2026-10"),
    ("BAD.001", "", "2026-10"),
    ("ONE.001", "", "2026-10"),
    ("ONE.001_S2", "", "2026-10"),
    ("RAS.001_S2", "", "2026-13"),
    ("IXB.001", "", "2026-10"),
]
