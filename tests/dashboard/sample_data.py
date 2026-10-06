"""Datos de ejemplo compartidos por las pruebas del dashboard."""

from datetime import datetime

from core.time_entries.models import TimeEntry
from core.utils.cell_types import CellValue

NOW = datetime(2026, 10, 2, 12, 0)

# Fechas como numero de serie de Sheets: 46023 = 2026-01-01.
SHEETS: dict[str, list[list[CellValue]]] = {
    "Proyectos": [
        [
            "ID_Proyecto",
            "Nombre",
            "Cliente",
            "Estado",
            "Budget_Hrs",
            "Fecha_Inicio",
            "Fecha_Fin_Estimada",
            "Servicio",
        ],
        ["P-1", "Alpha", "ACME", "Development", 100, 46023, 46265, "AER"],
        ["P-2", "Beta", "ACME", "Deployment", 50, 46023, 46280, "T&M"],
        ["P-3", "", "Globex", "Discovery", "", "", "", ""],
        ["P-4", "Delta", "Globex", "Cancelado", 80, 46023, 46100, "AER"],
        ["P-5", "Epsilon", "Initech", "Suspendido", "1,200", 46200, 46400, ""],
    ],
    "Riesgos": [
        ["ID_Riesgo", "ID_Proyecto", "Descripcion", "Impacto", "Estado"],
        ["R-1", "P-1", "Falta de accesos", "Medio", "Abierto"],
        ["R-2", "P-2", "Cliente sin UAT", "Alto", "Abierto"],
        ["R-3", "P-2", "Riesgo cerrado", "Alto", "Cerrado"],
        ["R-4", "P-3", "Alcance ambiguo", "Bajo", "Abierto"],
    ],
    "Recursos": [
        ["Proyecto", "Nombre del recurso", "Horas Estimadas"],
        ["P-1", "José Pérez", 80],
        ["P-1", "Ana Ruiz", 20],
        ["P-2", "Ana Ruiz", 40],
    ],
    "Sprints": [
        ["ID_Sprint", "ID_Proyecto", "Velocity", "Estado"],
        ["S-1", "P-1", 20, "En curso"],
        ["S-2", "P-2", 25, "En curso"],
        ["S-3", "P-2", 99, "Cerrado"],
    ],
    "Banda salarial": [
        ["Nombre", "Banda"],
        ["Jose Perez", "b2"],
        ["ana ruiz", "B3"],
    ],
    "Master rates": [
        ["Banda", "x", "y", "Costing Rate"],
        ["B2", "", "", 10],
        ["B3", "", "", 20],
    ],
    "Historico_Proyectos": [
        ["Project ID", "Delivery Manager"],
        ["P-1", "Laura"],
        ["P-1", "Otro"],
        ["P-2", "Mario"],
    ],
    "Dashboard_Historico_KPIs": [
        [
            "Fecha",
            "ProyectosActivos",
            "AvancePromedio",
            "HorasSemana",
            "RiesgosAltos",
            "FocoRojoSemana",
            "MargenPromedio",
        ],
        # Hace 9 y hace 7.5 dias: debe elegirse el de 7.5.
        [46288.5, 1, 10, 3, 0, 0, ""],
        [46290.0, 3, 20, 5, 2, 1, 12.5],
    ],
}


def build_entry(
    entry_id: str,
    project_id: str,
    resource_name: str,
    entry_date: datetime,
    duration_hours: float,
    is_billable: bool = True,
    costing_rate: float = 10.0,
) -> TimeEntry:
    return TimeEntry(
        entry_id=entry_id,
        project_id=project_id,
        resource_name=resource_name,
        entry_date=entry_date,
        duration_hours=duration_hours,
        is_billable=is_billable,
        costing_rate=costing_rate,
    )


TIME_ENTRIES = (
    build_entry("T-1", "P-1", "José Pérez", datetime(2026, 9, 30), 6),
    build_entry("T-2", "P-1", "José Pérez", datetime(2026, 9, 30), 5),
    build_entry("T-3", "P-1", "Ana Ruiz", datetime(2026, 8, 1), 30, True, 20),
    build_entry("T-4", "P-2", "Ana Ruiz", datetime(2026, 10, 1), 2),
    build_entry(
        "T-5",
        "P-2",
        "Ana Ruiz",
        datetime(2026, 10, 1),
        3,
        is_billable=False,
    ),
    build_entry("T-6", "P-2", "Ana Ruiz", datetime(2026, 7, 1), 60, True, 20),
)
