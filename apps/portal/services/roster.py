"""Personas vigentes del mes de Bandas/rol sobre las horas de GSE."""

from collections.abc import Mapping, Sequence
from typing import Any

from apps.capacidad.services.capacity_text import normalize_capacity_text
from apps.gse.services.cells import cell_at, norm, trimmed
from apps.gse.services.roster import find_band_column, read_roster_sheet
from core.sheets.protocols import SheetReader

"""BKD.120.025 - Plantilla del mes para Facturabilidad
La capacidad sale de las personas vigentes del mes en Bandas/rol (con su
ROL), solo si registraron horas positivas en el mes. Las horas salen
de Clockify (GSE), pero solo se cuentan las de esas personas y se agrupan
por el ROL de Bandas/rol. Quien no esta vigente ese mes no suma ni capacidad
ni horas.
"""

NO_ROLE = "Sin rol"


def attach_month_roster(
    gse: dict[str, Any],
    reader: SheetReader,
    month: str,
) -> dict[str, Any]:
    """Adjunta la plantilla de Bandas/rol sin depender de Recursos o MPB."""
    sheet = read_roster_sheet(reader, "Bandas/rol requiere Nombre y ROL.")
    column = find_band_column(sheet.headers, int(month[5:7]), month[:4])
    if column < 0:
        return {
            **gse,
            "plantillaAviso": (
                f"Bandas/rol no tiene banda para {month}. "
                "Se usan las personas con horas de GSE; "
                "no se conoce la plantilla vigente de ese mes."
            ),
        }
    name_column = sheet.headers.index("nombre")
    role_column = sheet.headers.index("rol")
    people = [
        {
            "nombre": trimmed(cell_at(row, name_column)),
            "rol": trimmed(cell_at(row, role_column)),
        }
        for row in sheet.data_rows
        if norm(cell_at(row, column)) not in ("", "baja", "na")
        and trimmed(cell_at(row, name_column))
        and trimmed(cell_at(row, role_column))
    ]
    bajas = [
        trimmed(cell_at(row, name_column))
        for row in sheet.data_rows
        if norm(cell_at(row, column)) == "baja"
        and trimmed(cell_at(row, name_column))
    ]
    return {**gse, "plantilla": people, "plantillaBajas": bajas}


def apply_roster(
    gse: Mapping[str, Any],
    people: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """
    Rehace las areas y el detalle de GSE con las personas vigentes.

    Args:
        gse: Resultado de gseObtenerMes.
        people: Personas vigentes de Bandas/rol (nombre y rol).

    Returns:
        Una copia de GSE con personas vigentes que registraron horas,
        incluidas las no facturables, y su detalle.
    """
    roster: dict[str, tuple[str, str]] = {}

    for person in people:
        name = _text(person.get("nombre"))

        if name:
            roster[normalize_capacity_text(name)] = (
                name,
                _text(person.get("rol")) or NO_ROLE,
            )

    detail: list[dict[str, Any]] = []
    hours: dict[str, float] = {}
    raw = gse.get("detalle")

    for item in raw if isinstance(raw, list) else []:
        if not isinstance(item, dict):
            continue

        key = normalize_capacity_text(item.get("recurso"))

        if key not in roster:
            continue

        detail.append({**item, "area": roster[key][1]})
        amount = item.get("horas")
        hours[key] = hours.get(key, 0.0) + (
            float(amount) if isinstance(amount, int | float) else 0.0
        )

    areas: dict[str, dict[str, Any]] = {}

    for key, (name, role) in roster.items():
        if hours.get(key, 0.0) <= 0:
            continue
        area = areas.setdefault(
            role,
            {"area": role, "recursos": 0, "personas": [], "categorias": []},
        )
        area["recursos"] += 1
        area["personas"].append({"nombre": name, "horas": hours.get(key, 0.0)})

    return {**gse, "areas": list(areas.values()), "detalle": detail}


def _text(value: object) -> str:
    """Texto sin espacios; vacio cuando no hay valor."""
    return "" if value is None else str(value).strip()
