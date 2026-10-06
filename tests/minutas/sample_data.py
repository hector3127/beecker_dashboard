"""Datos de prueba de Minutas IA.

expected_results.json es la salida de escanearMinutasNuevas(),
getMinutasViewData(), getProyectosConMinutas() y
extraerDatosPorReglas() del Apps Script original con estos datos y la
fecha 2026-10-02 12:00 (America/Mexico_City).
"""

from core.utils.cell_types import CellValue

GEMINI_NOTES = """﻿Notas
Daily Scrum - MCC.026 | Control de Accesos CCURE 2
oct 2, 2026
Invitado [Ana Pérez](mailto:ana@beecker.ai) [Luis Gómez](mailto:luis@beecker.ai)
Archivos adjuntos [Daily Scrum](https://calendar.google.com/x)
## Resumen
El equipo revisó el [avance](https://docs.google.com/x) del sprint.
Se acordó priorizar las pruebas.
### Detalles
* Avance de desarrollo: Se terminó el módulo de accesos. ([00:01:10](https://x))(00:01:10)
* Bloqueo en ambiente: El ambiente de QA está en espera de permisos. (00:03:16)
* Corto
- Revisión de pruebas: Se validaron los casos críticos del sprint.
Texto sin viñeta en detalles
**Próximos pasos:**
* [Ana Pérez] Configurar ambiente: Solicitar permisos a TI.
* [Luis Gómez] Ok
- Documentar los resultados de pruebas para el cliente
Notas generadas por Gemini
"""

NAME_ONLY_NOTES = """Reunión semanal
Invitado [Pedro](mailto:pedro@x.com)
Summary
Se habló del Robot RaaS Uno y del riesgo de retraso en la entrega final.
Details
* Riesgo de retraso: La entrega final podría moverse una semana. (01:02:03)
Next steps
* Revisar plan con el cliente esta semana
"""

SHORT_NOTES = "Notas cortas"

PROJECTS: list[list[CellValue]] = [
    ["ID_Proyecto", "Nombre"],
    ["MCC.026", "Control de Accesos CCURE 2"],
    ["RAS.001_S2", "Robot RaaS Uno"],
    ["AMK.008", "Robot AMK"],
]

MINUTE_HEADERS: list[CellValue] = [
    "ID_Minuta",
    "ID_Proyecto",
    "ID_Sprint",
    "Fecha_Reunion",
    "Fuente",
    "Doc_URL",
    "Asistentes",
    "Resumen_IA",
    "Riesgos_Detectados",
    "Pendientes",
    "Acuerdos",
    "WorkItems_Mencionados",
    "Sentimiento_Reunion",
    "Procesado",
]

SHEETS: dict[str, list[list[CellValue]]] = {
    "Proyectos": PROJECTS,
    "Minutas": [
        MINUTE_HEADERS,
        [
            "MIN-old00001",
            "AMK.008",
            "",
            46295,
            "Google Meet / Gemini",
            "https://docs.google.com/document/d/old",
            "Ana",
            "Resumen viejo",
            "",
            "",
            "Acuerdo A | Acuerdo B",
            "",
            "Neutral",
            True,
        ],
        [
            "MIN-old00002",
            "",
            "",
            "",
            "Manual",
            "",
            "",
            "Sin fecha",
            "",
            "",
            "",
            "",
            "",
            False,
        ],
    ],
    "Pendientes_Minutas": [
        [
            "ID_Pendiente",
            "ID_Minuta",
            "ID_Proyecto",
            "Descripcion",
            "Responsable",
            "Fecha_Compromiso",
            "Prioridad",
            "Estado",
        ],
        [
            "MIN-old00001-P0",
            "MIN-old00001",
            "AMK.008",
            "Pendiente viejo",
            "Ana",
            "",
            "Media",
            "Abierto",
        ],
    ],
    "Riesgos": [
        [
            "ID_Riesgo",
            "ID_Proyecto",
            "Descripcion",
            "Impacto",
            "Probabilidad",
            "Estado",
            "Responsable",
            "Fecha_Deteccion",
            "Fecha_Revision",
            "Plan_Mitigacion",
            "Origen",
        ],
        [
            "MIN-old00001-R0",
            "AMK.008",
            "Riesgo viejo",
            "Medio",
            "Media",
            "Abierto",
            "",
            "",
            "",
            "",
            "Regla-Minuta",
        ],
        ["", "AMK.008", "Fila vacia", "", "", "", "", "", "", "", "IA-Minuta"],
        ["RSK-1", "AMK.008", "Manual", "", "", "", "", "", "", "", "Manual"],
    ],
    "Historico_Riesgos": [["Timestamp", "ID_Riesgo", "Origen"]],
    "Log_Automatizaciones": [
        ["Fecha", "Proceso", "Resultado", "Detalle", "Ms"]
    ],
}

# Carpeta: (id, nombre, creado en ISO UTC, texto o None si falla).
FOLDER_ID = "folder-root"
DOCUMENTS: dict[str, list[tuple[str, str, str, str | None]]] = {
    "folder-root": [
        (
            "doc-mcc-0001xyz",
            "Daily MCC",
            "2026-10-02T15:00:00.000Z",
            GEMINI_NOTES,
        ),
        ("doc-old-0002xyz", "Ayer", "2026-10-01T15:00:00.000Z", GEMINI_NOTES),
        ("doc-short-003xy", "Corta", "2026-10-02T16:00:00.000Z", SHORT_NOTES),
        ("doc-fail-0004xy", "Sin permiso", "2026-10-02T17:00:00.000Z", None),
    ],
    "folder-sub": [
        (
            "doc-name-0005xy",
            "Semanal",
            "2026-10-02T05:30:00.000Z",
            NAME_ONLY_NOTES,
        ),
        # 2026-10-03 00:30 UTC sigue siendo 2 de octubre en Mexico.
        ("doc-late-0006xy", "Tarde", "2026-10-03T00:30:00.000Z", SHORT_NOTES),
    ],
}
SUBFOLDERS: dict[str, list[str]] = {
    "folder-root": ["folder-sub"],
    "folder-sub": [],
}

VIEW_FILTERS = [
    None,
    {"fecha": None, "proyecto": "Todos los proyectos"},
    {"fecha": "2026-10-02", "proyecto": None},
    {"fecha": None, "proyecto": "AMK.008"},
    {"fecha": "2026-10-01", "proyecto": "MCC.026"},
]
