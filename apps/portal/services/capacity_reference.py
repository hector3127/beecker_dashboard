"""Capacidad mensual por persona conciliada con el detalle GSE aprobado."""

from typing import Any

from apps.datastore.models import SheetSnapshot
from apps.gse.services.cells import norm

REFERENCE_SHEET = "Capacidad_Mensual_Referencia"
HEADERS = ["Mes", "Nombre", "ROL", "Capacidad", "Origen"]


def reference_people(month: str) -> list[dict[str, Any]] | None:
    """Devuelve el mes importado; None conserva el cálculo ordinario."""
    if not "2026-01" <= month <= "2026-09":
        return None
    snapshot = SheetSnapshot.objects.filter(name=REFERENCE_SHEET).first()
    if snapshot is None or not snapshot.rows or snapshot.rows[0] != HEADERS:
        return None
    rows = [row for row in snapshot.rows[1:] if row[0] == month]
    if not rows:
        return None
    return [
        {"nombre": row[1], "rol": row[2], "capacidad_horas": float(row[3])}
        for row in rows
    ]


def reference_note(month: str) -> str:
    """Etiqueta del corte histórico y alcance de la referencia."""
    return (
        f"Capacidad {month}: detalle mensual GSE importado por persona. "
        "Las horas consumidas y facturables provienen de Clockify."
        + (
            " Julio pendiente de ajustes manuales: "
            "-144 h de capacidad y +96 h AER."
            if month == "2026-07"
            else ""
        )
    )


def reference_capacity(people: list[dict[str, Any]]) -> dict[str, float]:
    """Índice por nombre normalizado para cruzar la plantilla."""
    return {
        norm(person["nombre"]): person["capacidad_horas"] for person in people
    }
