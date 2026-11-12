"""Importa el detalle mensual GSE sin copiar cifras del resumen ejecutivo."""

import hashlib
import math
import posixpath
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.datastore.models import SheetSnapshot
from apps.gse.services.cells import norm
from apps.portal.services.capacity_reference import HEADERS, REFERENCE_SHEET

NS = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
MONTHS = (
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
)


def read_reference(path: Path, year: int, through: int) -> list[list[object]]:
    """Lee valores guardados de capacidad, año y nombres con su contexto."""
    with zipfile.ZipFile(path) as archive:
        strings = [
            "".join(node.itertext())
            for node in ET.fromstring(archive.read("xl/sharedStrings.xml"))
        ]
        relations = {
            row.get("Id"): posixpath.normpath("xl/" + row.get("Target", ""))
            for row in ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        }
        book = ET.fromstring(archive.read("xl/workbook.xml"))
        sheet = next(
            (
                s
                for s in book.find("x:sheets", NS)
                if s.get("name") == "Detalle Hrs. Fact. por Servicio"
            ),
            None,
        )
        if sheet is None:
            raise CommandError("Falta Detalle Hrs. Fact. por Servicio.")
        key = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
        xml = ET.fromstring(archive.read(relations[sheet.get(key)]))

        def value(cell: ET.Element) -> str:
            node = cell.find("x:v", NS)
            if cell.get("t") == "inlineStr":
                return "".join(cell.find("x:is", NS).itertext())
            raw = node.text if node is not None else ""
            return strings[int(raw)] if cell.get("t") == "s" else raw or ""

        rows = [
            {
                "".join(filter(str.isalpha, cell.get("r", ""))): value(cell)
                for cell in row
            }
            for row in xml.find("x:sheetData", NS)
        ]
        columns = list(rows[1])
        start = next(
            (c for c, v in rows[0].items() if v in (str(year), f"{year}.0")),
            None,
        )
        if start is None or rows[1].get(start) != "Estimado":
            raise CommandError("No se encontró el bloque anual de capacidad.")
        index = columns.index(start)
        name_col, role_col = columns[index - 1], columns[index - 2]
        output: list[list[object]] = []
        seen = set()
        source = (
            path.name
            + " sha256="
            + hashlib.sha256(path.read_bytes()).hexdigest()
        )
        for row in rows[2:]:
            name, role = (
                row.get(name_col, "").strip(),
                row.get(role_col, "").strip(),
            )
            if not name or not role:
                continue
            if norm(name) in seen:
                raise CommandError(f"Persona repetida en el detalle: {name}.")
            seen.add(norm(name))
            for month in range(1, through + 1):
                column = columns[index + 7 * month]
                if norm(rows[0].get(column, "")) != MONTHS[month - 1]:
                    raise CommandError(
                        "Los encabezados mensuales no coinciden."
                    )
                raw = row.get(column, "")
                try:
                    hours = float(raw)
                except ValueError as error:
                    raise CommandError(
                        f"Capacidad no válida: {name}, mes {month}."
                    ) from error
                if not math.isfinite(hours) or hours < 0:
                    raise CommandError("Capacidad negativa o no finita.")
                output.append(
                    [f"{year}-{month:02d}", name, role, hours, source]
                )
        if not output:
            raise CommandError("No hay personas con capacidad mensual.")
        return output


class Command(BaseCommand):
    """Importación manual y transaccional de capacidades históricas."""

    help = "Importa la capacidad mensual por persona del Excel GSE."

    def add_arguments(self, parser):
        """Archivo y cobertura explícita del histórico."""
        parser.add_argument("archivo", type=Path)
        parser.add_argument("--year", type=int, required=True)
        parser.add_argument("--through", type=int, required=True)
        parser.add_argument("--from-month", type=int, default=1)

    def handle(self, *args, **options):
        """Conserva meses ajenos y reemplaza solo la cobertura importada."""
        if not 1 <= options["from_month"] <= options["through"] <= 12:
            raise CommandError("through debe estar entre 1 y 12.")
        rows = read_reference(
            options["archivo"], options["year"], options["through"]
        )
        rows = [
            row for row in rows if int(str(row[0])[5:]) >= options["from_month"]
        ]
        covered = {row[0] for row in rows}
        with transaction.atomic():
            existing = (
                SheetSnapshot.objects.select_for_update()
                .filter(name=REFERENCE_SHEET)
                .first()
            )
            previous = existing.rows[1:] if existing else []
            merged = [r for r in previous if r[0] not in covered] + rows
            SheetSnapshot.objects.update_or_create(
                name=REFERENCE_SHEET,
                defaults={
                    "rows": [HEADERS, *merged],
                    "row_count": len(merged) + 1,
                    "synced_at": timezone.now(),
                },
            )
        self.stdout.write(f"Importadas {len(rows)} capacidades mensuales.")
