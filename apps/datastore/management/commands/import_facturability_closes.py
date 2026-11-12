"""Lee las celdas publicadas de los dos reportes en el Excel GSE 25–26."""

from dataclasses import asdict
from datetime import date, timedelta
from pathlib import Path
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.portal.services.facturability import (
    _bar_height,
    build_month_facturability,
)
from apps.portal.services.facturability_closes import (
    GENERAL,
    SPECIALTY,
    publish,
    specialty_zero_lab,
)

XML = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def sheet_cells(book, sheet):
    """Lee los valores calculados que guarda Excel en la hoja."""
    strings = [
        "".join(part.text or "" for part in value.findall(".//s:t", XML))
        for value in ElementTree.fromstring(book.read("xl/sharedStrings.xml"))
    ]
    root = ElementTree.fromstring(book.read(f"xl/worksheets/sheet{sheet}.xml"))
    return {
        cell.attrib["r"]: strings[int(value.text)]
        if cell.get("t") == "s"
        else value.text
        for cell in root.findall(".//s:sheetData/s:row/s:c", XML)
        if (value := cell.find("s:v", XML)) is not None
        and value.text is not None
    }


def column(index):
    """Convierte un índice de columna en su referencia de Excel."""
    name = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(65 + remainder) + name
    return name


def general_closes(cells, people):
    """Conserva las métricas del resumen general publicado."""
    if (cells.get("R6"), cells.get("AK6")) != ("Resumen 2026", "Global"):
        raise ValueError("No se encontró el resumen general publicado.")
    for index in range(1, 10):
        month = f"2026-{index:02d}"
        row = index + 6
        value = {
            key: float(cells[f"{key}{row}"])
            for key in (
                "Q",
                "S",
                "T",
                "U",
                "V",
                "X",
                "Y",
                "Z",
                "AA",
                "AB",
                "AC",
                "AD",
                "AE",
                "AI",
                "AJ",
                "AK",
            )
        }
        metric = asdict(build_month_facturability(month, {}))
        percent = value["AK"] * 100
        metric.update(
            person_hours=value["Q"],
            capacity=value["S"],
            fixed_hours=value["T"],
            fixed_percent=value["U"] * 100,
            fixed_hc=value["V"],
            variable_capacity=value["X"],
            variable_hours=value["Y"],
            variable_percent=value["Z"] * 100,
            variable_hc=value["AA"],
            service_hours=[value[key] for key in ("AB", "AC", "AD", "AE")],
            free_hours=value["AI"],
            free_fte=value["AJ"],
            global_percent=percent,
            bar_height=_bar_height(percent),
            resources=people[month],
            notice="Cierre publicado de GSE.",
        )
        yield month, GENERAL, metric


def specialty_closes(cells):
    """Lee los bloques mensuales de especialidad del reporte."""
    groups = ((4, range(4)), (16, range(1, 4)), (28, range(3)))
    fields = (
        "capacity",
        "headcount",
        "fixed_hours",
        "fixed_percent",
        "fixed_hc",
        "variable_hours",
        "variable_percent",
        "variable_hc",
        "free_fte",
    )
    expected = ["2025-12", *(f"2026-{index:02d}" for index in range(1, 10))]
    months = []
    for header, indices in groups:
        for index in indices:
            first = 2 + index * 9
            serial = cells[f"{column(first)}{header}"]
            month = (
                date(1899, 12, 30) + timedelta(days=float(serial))
            ).isoformat()[:7]
            rows = []
            for row in range(header + 2, header + 8):
                name = cells[f"A{row}"]
                if name == "Lab IA" and month >= "2026-08":
                    rows.append(asdict(specialty_zero_lab()))
                    continue
                values = {
                    field: float(cells[f"{column(first + offset)}{row}"])
                    for offset, field in enumerate(fields)
                }
                values["fixed_percent"] *= 100
                values["variable_percent"] *= 100
                rows.append(
                    {"name": "QA" if name == "TT & CR" else name, **values}
                )
            months.append((month, SPECIALTY, rows))
    if [month for month, _, _ in months] != expected:
        raise ValueError(
            "Los meses del histórico por especialidad no coinciden."
        )
    return months


class Command(BaseCommand):
    """Importa ambas tablas publicadas sin reemplazar revisiones."""

    help = "Importa los cierres publicados en el Excel GSE 25–26."

    def add_arguments(self, parser):
        """Declara la ruta al Excel original."""
        parser.add_argument("workbook", type=Path)

    def handle(self, *args, **options):
        """Valida y publica el histórico de GSE."""
        try:
            with ZipFile(options["workbook"]) as book:
                specialty = specialty_closes(sheet_cells(book, 7))
                people = {
                    month: int(sum(row["headcount"] for row in rows))
                    for month, _, rows in specialty
                }
                general = list(general_closes(sheet_cells(book, 5), people))
        except (
            OSError,
            BadZipFile,
            KeyError,
            ValueError,
            ElementTree.ParseError,
        ) as error:
            raise CommandError(
                f"No se pudieron leer los cierres GSE: {error}"
            ) from error
        with transaction.atomic():
            count = sum(
                publish(
                    month,
                    view,
                    metrics,
                    "GSE OP 25–26 · "
                    + (
                        "2. Capacity & Demand"
                        if view == GENERAL
                        else "Indicadores PPT C-suite"
                    ),
                )
                for month, view, metrics in [*general, *specialty]
            )
        self.stdout.write(f"{count} cierres históricos nuevos.")
