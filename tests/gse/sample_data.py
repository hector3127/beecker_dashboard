"""Datos de prueba de GSE, tambien usados para correr el .gs original."""

import copy

CONNECTION = "ws1_abcdef0123456789"
WORKSPACE = "ws1"

ROSTER = [
    ["Bandas por rol"],
    [
        "Nombre",
        "Correo",
        "ROL",
        "ID Clockify",
        "Septiembre 2026",
        "Octubre 2026",
    ],
    ["Ana Pérez", "a@x", "QA", "u1", "B2", "B3"],
    ["Luis Gómez", "l@x", "QA", "u2", "B1", "Baja"],
    ["María Núñez", "m@x", "Desarrollo", "u3", "B4", "B4"],
    ["Pedro Ruiz", "p@x", "Desarrollo", "", "B2", "B2"],
    ["Ana Pérez", "dup", "QA", "u1", "B9", "B9"],
    ["", "", "", "", "", ""],
]

CATALOG = [
    [
        "Cliente",
        "Operaciones",
        "Tipo de Proyecto",
        "ID_Proyecto",
        "",
        "",
        "",
        "",
        "Servicio",
    ],
    [
        "A",
        "Optimización",
        "Facturable",
        "AMK.008_S4",
        "",
        "",
        "",
        "",
        "Servicio A",
    ],
    ["B", "Laboratorio", "No Facturable", "LAB.001", "", "", "", "", ""],
    [
        "C",
        "Agentes Autónomos",
        "Facturable",
        "AGT.003",
        "",
        "",
        "",
        "",
        "Svc B",
    ],
    ["D", "Delivery", "Facturable", "AMK.008", "", "", "", "", "Svc Base"],
    ["D", "Delivery", "Facturable", "AMK.008", "", "", "", "", ""],
    ["E", "Delivery", "Facturable", "XYZ.010_CR1", "", "", "", "", "Svc CR"],
    ["F", "Delivery", "Facturable", "", "", "", "", "", "sin id"],
]

BASE_HEADERS = [
    "Project",
    "User",
    "Start Date",
    "Duration (decimal)",
    "Task",
    "Tags",
    "Billable",
    "ID Registro",
    "ID Clockify",
    "Workspace",
    "Conexión GSE",
    "Actualizado",
]


def base_row(values, connection=CONNECTION):
    """Fila de la base: 9 datos y las tres columnas de control."""
    return [*values, WORKSPACE, connection, "2026-10-01T10:00:00.000Z"]


BASE = [
    BASE_HEADERS,
    base_row(
        [
            "AMK.008_S4",
            "Ana Pérez",
            "2026-09-03",
            4.5,
            "dev",
            "a, b",
            "Yes",
            "r1",
            "u1",
        ]
    ),
    base_row(
        [
            "AMK.008",
            "Ana Pérez",
            "05/09/2026",
            3,
            "tarea_S4",
            "",
            "Yes",
            "r2",
            "u1",
        ]
    ),
    base_row(
        ["LAB.001", "Luis Gómez", "2026-09-04", 8, "", "", "No", "r3", "u2"]
    ),
    base_row(
        ["Vacaciones", "Luis Gómez", "2026-09-05", 8, "", "", "No", "r4", "u2"]
    ),
    base_row(
        [
            "000-Interno",
            "María Núñez",
            "2026-09-05",
            2,
            "",
            "interno",
            "No",
            "r5",
            "u3",
        ]
    ),
    base_row(
        [
            "Administrative Activities",
            "María Núñez",
            "2026-09-06",
            1.25,
            "",
            "",
            "No",
            "r6",
            "u3",
        ]
    ),
    base_row(
        [
            "ZZZ.999",
            "Pedro Ruiz",
            "2026-09-07",
            6,
            "Planning_S2",
            "",
            "Yes",
            "r7",
            "",
        ]
    ),
    base_row(
        [
            "AMK.008_S4",
            "Desconocido Z",
            "2026-09-07",
            2,
            "",
            "",
            "Yes",
            "r8",
            "uX",
        ]
    ),
    base_row(
        ["AMK.008_S4", "Ana Pérez", "2026-09-08", 0, "", "", "Yes", "r9", "u1"]
    ),
    base_row(
        [
            "AMK.008_S4",
            "Ana Pérez",
            "2026-09-03",
            4.5,
            "dev",
            "a, b",
            "Yes",
            "r1",
            "u1",
        ]
    ),
    base_row(
        ["AMK.008_S4", "Ana Pérez", "2026-10-01", 5, "", "", "Yes", "r11", "u1"]
    ),
    base_row(
        ["AGT.003", "Luis Gómez", "2026-10-01", 3, "", "", "Yes", "r12", "u2"]
    ),
    base_row(
        [
            "AMK.008_S4",
            "Ana Pérez",
            "2026-10-01",
            7,
            "",
            "",
            "Yes",
            "r13",
            "u1",
        ],
        "otra_conexion",
    ),
    base_row(
        [
            "Pre-Venta Acme",
            "María Núñez",
            "2026-10-02",
            2.5,
            "",
            "inv comercial, x",
            "No",
            "r14",
            "u3",
        ]
    ),
    base_row(
        [
            "pre venta",
            "María Núñez",
            "2026-09-09",
            1.5,
            "",
            "",
            "No",
            "r15",
            "u3",
        ]
    ),
    base_row(
        ["Interno", "Luis Gómez", "fecha mala", 1, "", "", "No", "r16", "u2"]
    ),
    base_row(
        [
            "Investigación",
            "Luis Gómez",
            "2026-09-10",
            2,
            "",
            "inversion operaciones",
            "No",
            "r17",
            "u2",
        ]
    ),
    base_row(
        [
            "XYZ.010",
            "Ana Pérez",
            "2026-09-11",
            1,
            "Cambio_CR1",
            "",
            "Yes",
            "r18",
            "u1",
        ]
    ),
    base_row(
        [
            "XYZ.010_CR2",
            "Ana Pérez",
            "2026-09-12",
            2,
            "",
            "",
            "Yes",
            "r19",
            "u1",
        ]
    ),
]

CONTROL = [
    ["Clave", "Mes", "IDs JSON", "Actualizado", "Registros"],
    [
        f"{CONNECTION}|2026-09|null",
        "2026-09",
        "null",
        "2026-10-01T10:00:00.000Z",
        9,
    ],
    [
        f'{CONNECTION}|2026-10|["u1","u2"]',
        "2026-10",
        '["u1","u2"]',
        "2026-10-02T17:30:00.000Z",
        3,
    ],
    [f"{CONNECTION}|2026-07|null", "2026-07", "null", "", 0],
]

LEGACY_HEADERS = [
    "Project",
    "Client",
    "Description",
    "Task",
    "User",
    "Group",
    "Email",
    "Tags",
    "Billable",
    "Start Date",
    "Start Time",
    "End Date",
    "End Time",
    "Duration (h)",
    "Duration (decimal)",
]
LEGACY = [
    ["Reporte Clockify"],
    LEGACY_HEADERS,
    [
        "AMK.008_S4",
        "",
        "",
        "x",
        "Ana Pérez",
        "",
        "",
        "a;b",
        "Yes",
        "03/09/2026",
        "",
        "",
        "",
        "",
        4.5,
    ],
    [
        "LAB.001",
        "",
        "",
        "",
        "Luis Gómez",
        "",
        "",
        "",
        "No",
        "2026-09-04",
        "",
        "",
        "",
        "",
        8,
    ],
    [
        "AMK.008",
        "",
        "",
        "t_S4",
        "Desconocido",
        "",
        "",
        "",
        "si",
        "05-09-2026",
        "",
        "",
        "",
        "",
        1,
    ],
    [
        "AMK.008",
        "",
        "",
        "",
        "Ana Pérez",
        "",
        "",
        "",
        "Yes",
        "2026-10-05",
        "",
        "",
        "",
        "",
        3,
    ],
]

SHEETS = {
    "Bandas/rol": ROSTER,
    "CatalagoProyectos": CATALOG,
    "08.Base Clockify 2026": BASE,
    "GSE_Base_Control": CONTROL,
}


def build_datasets():
    """Variantes de las hojas para las distintas pruebas."""
    main = copy.deepcopy(SHEETS)
    no_catalog = copy.deepcopy(SHEETS)
    del no_catalog["CatalagoProyectos"]
    contradiction = copy.deepcopy(SHEETS)
    contradiction["CatalagoProyectos"].append(
        ["Z", "Otra", "Facturable", "AMK.008", "", "", "", "", ""],
    )
    legacy = copy.deepcopy(SHEETS)
    legacy["08.Base Clockify 2026"] = copy.deepcopy(LEGACY)
    del legacy["GSE_Base_Control"]
    legacy_bad = copy.deepcopy(legacy)
    legacy_bad["08.Base Clockify 2026"].append(
        [
            "AMK.008",
            "",
            "",
            "",
            "Ana Pérez",
            "",
            "",
            "",
            "Yes",
            "2026-09-20",
            "",
            "",
            "",
            "",
            "1,5",
        ],
    )
    no_base = copy.deepcopy(SHEETS)
    del no_base["08.Base Clockify 2026"]
    contradictory_suffix = copy.deepcopy(SHEETS)
    contradictory_suffix["08.Base Clockify 2026"].append(
        base_row(
            [
                "AMK.008",
                "Ana Pérez",
                "2026-09-13",
                1,
                "a_S1 b_S2",
                "",
                "Yes",
                "r20",
                "u1",
            ]
        ),
    )
    bad_schema = copy.deepcopy(SHEETS)
    bad_schema["08.Base Clockify 2026"][0] = ["Project", "User"]
    no_roster = copy.deepcopy(SHEETS)
    del no_roster["Bandas/rol"]
    duplicate_id = copy.deepcopy(SHEETS)
    duplicate_id["Bandas/rol"].append(
        ["Otra Persona", "o@x", "QA", "u1", "", ""]
    )

    return {
        "main": main,
        "no_catalog": no_catalog,
        "contradiction": contradiction,
        "legacy": legacy,
        "legacy_bad": legacy_bad,
        "no_base": no_base,
        "contradictory_suffix": contradictory_suffix,
        "bad_schema": bad_schema,
        "no_roster": no_roster,
        "duplicate_id": duplicate_id,
    }


# (conjunto de hojas, mes, fuente, forzar, area)
MONTH_SCENARIOS = [
    ("main", "2026-09", "sheet", False, ""),
    ("main", "2026-09", "sheet", False, "QA"),
    ("main", "2026-09", "sheet", False, "Desarrollo"),
    ("main", "2026-10", "sheet", False, "QA"),
    ("main", "2026-10", "sheet", False, "Desarrollo"),
    ("main", "2026-08", "sheet", False, ""),
    ("main", "2026-13", "sheet", False, ""),
    ("main", "2026-09", "sheet", False, "Inexistente"),
    ("no_catalog", "2026-09", "sheet", False, ""),
    ("contradiction", "2026-09", "sheet", False, ""),
    ("legacy", "2026-09", "sheet", False, ""),
    ("legacy", "2026-10", "sheet", False, "QA"),
    ("legacy_bad", "2026-09", "sheet", False, ""),
    ("no_base", "2026-09", "sheet", False, ""),
    ("contradictory_suffix", "2026-09", "sheet", False, ""),
    ("bad_schema", "2026-09", "sheet", False, ""),
    ("no_roster", "2026-09", "sheet", False, ""),
    ("duplicate_id", "2026-09", "sheet", False, ""),
]

# (conjunto de hojas, ano, area, posicion del bloque, filas esperadas)
BATCH_SIZE = 4
BATCH_SCENARIOS = [
    ("main", 2026, "", 0, None),
    ("main", 2026, "", 4, 19),
    ("main", 2026, "", 8, 19),
    ("main", 2026, "", 12, 19),
    ("main", 2026, "", 16, 19),
    ("main", 2026, "", 20, 19),
    ("main", 2026, "QA", 0, None),
    ("main", 2026, "QA", 4, None),
    ("main", 2026, "", 0, 5),
    ("main", 1999, "", 0, None),
    ("main", 2026, "", -1, None),
    ("main", 2025, "", 0, None),
    ("no_catalog", 2026, "", 0, None),
    ("contradiction", 2026, "", 0, None),
    ("contradictory_suffix", 2026, "", 16, None),
    ("legacy", 2026, "", 0, None),
    ("bad_schema", 2026, "", 0, None),
    ("no_roster", 2026, "", 0, None),
    ("duplicate_id", 2026, "", 0, None),
]

# (conjunto de hojas, ano, area)
YEAR_SCENARIOS = [
    ("main", 2026, ""),
    ("main", 2026, "QA"),
    ("main", 2025, ""),
    ("main", 2027, ""),
    ("main", 1999, ""),
    ("legacy", 2026, ""),
]
