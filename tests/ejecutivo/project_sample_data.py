"""Datos de prueba del detalle y del dashboard ejecutivo del proyecto.

Los resultados esperados (project_expected.json) se obtuvieron
ejecutando getDetalleProyectoCompleto() y getDashboardEjecutivoProyecto()
del Apps Script original con estos mismos datos y la fecha
2026-10-02 12:00 (America/Mexico_City).
"""

from datetime import date

from core.utils.cell_types import CellValue


def serial(year, month, day):
    """Numero de serie de Sheets de una fecha."""
    return (date(year, month, day) - date(1899, 12, 30)).days


PROJECT_HEADERS: list[CellValue] = [
    "ID_Proyecto",
    "Nombre",
    "Cliente",
    "Estado",
    "Servicio",
    "Budget_Hrs",
    "Fecha_Inicio",
    "Fecha_Fin_Estimada",
    "Sponsor",
    "Scrum_Master",
    "Extra",
    "Go Live",
    "Kickoff",
]

SHEETS: dict[str, list[list[CellValue]]] = {
    "Proyectos": [
        PROJECT_HEADERS,
        [
            "AMK.008",
            "Robot AMK",
            "ACME",
            "Development",
            "T&M",
            100,
            serial(2026, 7, 1),
            serial(2026, 12, 31),
            "Laura",
            "Pedro SM",
            "",
            "2026-11-15::Salida | 2026-12-01",
            "2026-07-01::Inicio",
        ],
        [
            "RAS.001_S2",
            "RaaS Uno",
            "Beta",
            "Development",
            "RaaS",
            "80",
            serial(2026, 9, 1),
            serial(2026, 10, 10),
            "",
            "",
        ],
        [
            "CLS.001",
            "",
            "",
            "Cancelado",
            "IXB",
            0,
            "",
            "",
        ],
        [
            "SUS.001",
            "Suspendido",
            "",
            "Suspendido",
            "Otro",
            10,
            serial(2026, 1, 1),
            serial(2026, 10, 15),
        ],
        [
            "OVR.001",
            "Sobreconsumo",
            "",
            "Development",
            "AER",
            5,
            serial(2026, 1, 1),
            serial(2026, 9, 1),
        ],
        [
            "PAC.001",
            "Ritmo",
            "",
            "Development",
            "AER",
            1000,
            serial(2026, 8, 1),
            serial(2026, 11, 30),
        ],
    ],
    "Recursos": [
        ["Proyecto", "Posicion", "Nombre del recurso", "Horas Estimadas"],
        ["AMK.008", "Developer", "Ana Pérez", 50],
        ["AMK.008", "QA Tester", "Luis Gómez", "20"],
        ["AMK.008", "", "Sin Horas", 10],
        ["AMK.008", "Project Manager", "María López", 0],
        ["RAS.001_S2", "Business Analyst", "Ana Pérez", 30],
        ["RAS.001_S2", "Arquitecto", "Luis Gómez", 5],
        ["OVR.001", "Developer", "Ana Pérez", 1],
    ],
    "Banda salarial": [
        ["Nombre", "Banda"],
        ["Ana Perez", "B2"],
        ["luis gómez", " b1 "],
    ],
    "Master rates": [
        ["Banda", "", "", "Costing Rate"],
        ["B1", "", "", 15],
        ["B2", "", "", "22.5"],
    ],
    "Historico_Proyectos": [
        [
            "Delivery Manager",
            "Account",
            "Project ID",
            "Service",
            "Project Name",
            "Marca",
            "Status",
            "Start",
            "Finish",
        ],
        [
            "DM Uno",
            "ACME",
            "AMK.008",
            "T&M",
            "Robot",
            "START",
            "Discovery EST",
            serial(2026, 7, 1),
            serial(2026, 7, 31),
        ],
        [
            "",
            "ACME",
            "AMK.008",
            "T&M",
            "Robot",
            "",
            "Development EST",
            serial(2026, 8, 1),
            serial(2026, 11, 15),
        ],
        [
            "",
            "ACME",
            "AMK.008",
            "T&M",
            "Robot",
            "",
            "Discovery",
            serial(2026, 7, 2),
            serial(2026, 8, 3),
        ],
        [
            "",
            "ACME",
            "AMK.008",
            "T&M",
            "Robot",
            "",
            "Development",
            serial(2026, 8, 4),
            "",
        ],
        [
            "DM Raas",
            "Beta",
            "RAS.001_S2",
            "RaaS",
            "RaaS",
            "",
            "Discovery EST",
            serial(2026, 9, 1),
            serial(2026, 9, 15),
        ],
        [
            "",
            "Beta",
            "RAS.001_S2",
            "RaaS",
            "RaaS",
            "",
            "Development EST",
            serial(2026, 9, 16),
            serial(2026, 10, 5),
        ],
        [
            "",
            "Beta",
            "RAS.001_S2",
            "RaaS",
            "RaaS",
            "",
            "Deployment EST",
            serial(2026, 10, 6),
            serial(2026, 10, 10),
        ],
        [
            "",
            "Beta",
            "RAS.001_S2",
            "RaaS",
            "RaaS",
            "",
            "Discovery",
            serial(2026, 9, 1),
            serial(2026, 9, 14),
        ],
        [
            "",
            "Beta",
            "RAS.001_S2",
            "RaaS",
            "RaaS",
            "",
            "Development",
            serial(2026, 9, 15),
            "",
        ],
        [
            "",
            "Beta",
            "RAS.001_S2",
            "RaaS",
            "RaaS",
            "",
            "Suspendido",
            serial(2026, 9, 20),
            serial(2026, 9, 22),
        ],
    ],
    "Riesgos": [
        [
            "ID_Proyecto",
            "Descripcion",
            "Impacto",
            "Probabilidad",
            "Estado",
        ],
        ["AMK.008", "Bajo uno", "Bajo", "Alta", "Abierto"],
        ["AMK.008", "Alto uno", "Alto", "Media", "Abierto"],
        ["AMK.008", "Cerrado", "Alto", "Alta", "Cerrado"],
        ["AMK.008", "Medio uno", "Medio", "", "Abierto"],
        ["AMK.008", "Sin impacto", "", "", "Abierto"],
        ["AMK.008", "Alto dos", "Alto", "Baja", "Abierto"],
        ["AMK.008", "Medio dos", "Medio", "Baja", "Abierto"],
    ],
    "Pendientes_Minutas": [
        ["ID_Proyecto", "Estado"],
        ["AMK.008", "Abierto"],
        ["AMK.008", "Cerrado"],
        ["RAS.001_S2", "Abierto"],
    ],
}

# Historico con un titulo arriba: el lector general no encuentra filas y
# los proyectos IXB/RaaS usan las etapas de las columnas A:I.
TITLED_HISTORY = [["Historico de proyectos"], *SHEETS["Historico_Proyectos"]]

DATE_COLUMNS = {
    "Proyectos": ["Fecha_Inicio", "Fecha_Fin_Estimada"],
    "Historico_Proyectos": ["Start", "Finish"],
}


def entry(proyecto, recurso, fecha, duracion, billable=True, task="", tags=()):
    """Registro de Clockify con los campos del original."""
    return {
        "proyecto": proyecto,
        "recurso": recurso,
        "fecha": fecha,
        "duracion": duracion,
        "billable": billable,
        "task": task,
        "tags": list(tags),
    }


PORTFOLIO = [
    entry("AMK.008", "Ana Pérez", "2026-09-01", 30.25),
    entry("AMK.008", "Luis Gómez", "2026-09-02", 12.5),
    entry("AMK.008", "Luis Gómez", "2026-09-03", 4, billable=False),
    entry("RAS.001_S2", "Ana Pérez", "2026-09-10", 18),
    entry("OVR.001", "Ana Pérez", "2026-03-01", 7.333),
    entry("PAC.001", "Ana Pérez", "2026-09-01", 100),
    entry("OTRO.1", "Ana Pérez", "2026-09-01", 50),
]

PROJECT_ENTRIES = {
    "AMK.008": [
        entry("AMK.008", "Ana Pérez", "2026-09-01", 30.25, task="S2"),
        entry("AMK.008", "ana perez", "2026-09-05", 1.105),
        entry("AMK.008", "Luis Gómez", "2026-09-02", 12.5),
        entry("AMK.008", "Luis Gómez", "2026-09-03", 4, billable=False),
        entry("AMK.008", "Externo", "2026-09-03", 2),
    ],
    "RAS.001_S2": [
        entry("RAS.001_S2", "Ana Pérez", "2026-09-10", 10, task="Fase S2"),
        entry("RAS.001_S2", "Ana Pérez", "2026-09-11", 5, tags=["S1"]),
        entry("RAS.001_S2", "Ana Pérez", "2026-09-12", 3),
        entry("RAS.001_S2", "Luis Gómez", "2026-09-12", 6, task="CR1"),
        entry("RAS.001_S2", "Luis Gómez", "2026-09-13", 2, billable=False),
    ],
    "OVR.001": [entry("OVR.001", "Ana Pérez", "2026-03-01", 7.333)],
}

# (funcion, ID, hojas reemplazadas)
SCENARIOS = [
    ("detalle", "AMK.008", {}),
    ("detalle", "RAS.001_S2", {}),
    ("detalle", "NOEXISTE", {}),
    ("detalle", "ERR.001", {}),
    ("detalle", "AMK.008", {"Recursos": None}),
    ("ejecutivo", "AMK.008", {}),
    ("ejecutivo", "RAS.001_S2", {}),
    ("ejecutivo", "RAS.001_S2", {"Historico_Proyectos": TITLED_HISTORY}),
    ("ejecutivo", "CLS.001", {}),
    ("ejecutivo", "SUS.001", {}),
    ("ejecutivo", "OVR.001", {}),
    ("ejecutivo", "PAC.001", {}),
    ("ejecutivo", "NOEXISTE", {}),
    ("ejecutivo", "AMK.008", {"Riesgos": None, "Pendientes_Minutas": None}),
]

RISK_HEADERS = [
    "ID_Riesgo",
    "ID_Proyecto",
    "Descripcion",
    "Impacto",
    "Probabilidad",
    "Estado",
    "Responsable",
    "Fecha_Deteccion",
    "Origen",
]

WRITE_SHEETS: dict[str, list[list[CellValue]]] = {
    "Proyectos": SHEETS["Proyectos"],
    "Riesgos": [list(RISK_HEADERS)],
    "Historico_Riesgos": [["Timestamp", "ID_Riesgo", "Impacto", "Origen"]],
}

# (funcion del original, argumentos). Las fechas llevan hora para que el
# original no las recorra un dia y las observaciones van vacias; esas dos
# diferencias se prueban aparte en test_milestone_writer.py.
WRITE_OPERATIONS = [
    ("obtenerTiposHitosExistentes", []),
    (
        "guardarHitosAdicionalesLote",
        [
            "AMK.008",
            [
                {"tipo": "Go Live", "fechaISO": "2026-11-20T10:00:00"},
                {"tipo": "🎯 Nuevo", "fechaISO": "2026-12-01T09:00:00"},
                {
                    "tipo": "🎯 nuevo",
                    "fechaISO": "sin fecha",
                    "observacion": "",
                },
                {"tipo": "  ", "fechaISO": "2026-12-01T09:00:00"},
            ],
        ],
    ),
    (
        "guardarHitosAdicionalesLote",
        [
            "ras.001_s2",
            [{"tipo": "Kickoff", "fechaISO": "2026-09-01T08:00:00"}],
        ],
    ),
    (
        "editarHitoAdicional",
        ["AMK.008", "go live", 1, "2026-12-05T10:00:00", ""],
    ),
    (
        "editarHitoAdicional",
        ["AMK.008", "Go Live", 5, "2026-12-05T10:00:00", ""],
    ),
    ("eliminarHitoAdicional", ["AMK.008", "Go Live", 0]),
    ("eliminarHitoAdicional", ["AMK.008", "No existe", 0]),
    ("eliminarHitoAdicional", ["CLS.001", "Kickoff", 0]),
    ("guardarHitosAdicionalesLote", ["NOEXISTE", [{"tipo": "Go Live"}]]),
    ("guardarHitosAdicionalesLote", ["", [{"tipo": "Go Live"}]]),
    ("guardarHitosAdicionalesLote", ["AMK.008", []]),
    (
        "agregarRiesgoManual",
        ["AMK.008", " Riesgo nuevo ", "Alto", "Media", " Ana "],
    ),
    ("agregarRiesgoManual", ["AMK.008", "Otro", "Critico", "Media", ""]),
    ("agregarRiesgoManual", ["AMK.008", "   ", "Alto", "Media", ""]),
    ("agregarRiesgoManual", ["", "Algo", "Alto", "Media", ""]),
    ("obtenerTiposHitosExistentes", []),
]
