"""Publica un cierre de Facturabilidad cuando se validaron las fuentes."""

import csv
from collections import defaultdict
from dataclasses import asdict
from datetime import date
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.capacidad.services.capacity_text import normalize_capacity_text
from apps.datastore.models import (
    ClockifyMonthSync,
    ClockifyTimeEntry,
    SheetSnapshot,
)
from apps.gse.services.roster import find_band_column, read_roster_sheet
from apps.portal.services.facturability import (
    OPERATIONAL_KEYS,
    _detail_rows,
    build_month_facturability,
    build_specialties,
    display_role,
    role_key,
)
from apps.portal.services.facturability_closes import (
    GENERAL,
    SPECIALTY,
    publish,
    published_months,
    specialty_zero_lab,
)
from apps.portal.services.facturability_loader import read_gse_month
from apps.portal.services.roster import apply_roster
from core.sheets.factory import build_sheet_repository


def employee_detail(month, gse, metric):
    """Desglosa el cierre y las fechas de los registros válidos."""
    rows = {}
    for person in gse["plantilla"]:
        role = person["rol"]
        if role_key(role) not in OPERATIONAL_KEYS:
            continue
        key = normalize_capacity_text(person["nombre"])
        rows[key] = [
            person["nombre"],
            display_role(role),
            person.get("capacidad_horas", metric.person_hours),
            0.0,
            0.0,
            0.0,
        ]
    for item in _detail_rows(gse, OPERATIONAL_KEYS):
        key = normalize_capacity_text(item["name"])
        row = rows.setdefault(
            key, [item["name"], display_role(item["role"]), 0, 0.0, 0.0, 0.0]
        )
        if item["service"] == "AER":
            row[3 if item["billable"] else 4] += item["hours"]
        elif item["billable"]:
            row[5] += item["hours"]

    dates = defaultdict(set)
    for name, day in (
        ClockifyTimeEntry.objects.filter(
            month=month + "-01",
            duration_seconds__gt=0,
            entry_date__isnull=False,
        )
        .exclude(project_id="61d5aa2596aafe5141cd7413")
        .values_list("user_name", "entry_date")
    ):
        key = normalize_capacity_text(name)
        if key in rows:
            dates[key].add(day.isoformat())
    return [
        [*row, row[2] - row[3] - row[5], " | ".join(sorted(dates[key]))]
        for key, row in sorted(rows.items())
    ]


class Command(BaseCommand):
    """Valida las fuentes antes de publicar el cierre."""

    help = "Publica los dos cierres cuando Clockify y GSE están completos."

    def add_arguments(self, parser):
        """Declara el mes, la confirmación y la ruta de exportación."""
        parser.add_argument("month")
        parser.add_argument("--fuentes-completas", action="store_true")
        parser.add_argument("--revision", metavar="MOTIVO")
        parser.add_argument("--csv", type=Path)

    def handle(self, *args, **options):
        """Publica las métricas del mes terminado."""
        month = options["month"]
        try:
            first = date.fromisoformat(month + "-01")
        except ValueError as error:
            raise CommandError("Usa AAAA-MM.") from error
        today = timezone.localdate()
        if first >= today.replace(day=1):
            raise CommandError("El mes debe haber terminado.")
        if not options["fuentes_completas"]:
            raise CommandError(
                "Confirma Clockify y GSE con --fuentes-completas."
            )
        sync = ClockifyMonthSync.objects.filter(
            month=first, run__status="ok"
        ).first()
        if (
            not sync
            or timezone.localtime(sync.synced_at).date().replace(day=1) <= first
            or sync.entries_count <= 0
            or ClockifyTimeEntry.objects.filter(month=first).count()
            != sync.entries_count
        ):
            raise CommandError(
                "Clockify requiere una sincronización completa tras el cierre."
            )
        if not SheetSnapshot.objects.filter(
            name="Bandas/rol", row_count__gt=0
        ).exists():
            raise CommandError("Falta la copia de Bandas/rol.")
        sheet = read_roster_sheet(build_sheet_repository(), "Falta Bandas/rol.")
        if find_band_column(sheet.headers, first.month, str(first.year)) < 0:
            raise CommandError("Bandas/rol no tiene el mes solicitado.")
        raw = read_gse_month(month, from_store=True)
        if not raw.get("ok") or not raw.get("plantilla"):
            raise CommandError(f"GSE incompleto para {month}.")
        gse = apply_roster(raw, raw["plantilla"])
        scope = (OPERATIONAL_KEYS, None)
        general = build_month_facturability(month, gse, scope=scope)
        specialties = build_specialties(gse, month, scope)
        if month >= "2026-08":
            specialties += (specialty_zero_lab(),)
        if not general.capacity or not specialties:
            raise CommandError(f"El cierre {month} carece de capacidad.")
        source = "Clockify + GSE / Bandas/rol"
        revision = options["revision"]
        if revision:
            source += f" · {revision}"
        if len(source) > 255:
            raise CommandError("El motivo de revisión es demasiado largo.")
        general_values = asdict(general)
        general_values["service_hours"] = list(general.service_hours)
        if not revision:
            for view, values in (
                (GENERAL, general_values),
                (SPECIALTY, [asdict(row) for row in specialties]),
            ):
                previous = published_months(view, [month]).get(month)
                if previous is not None and previous != values:
                    raise CommandError(
                        "El cierre cambió. Confirma con --revision."
                    )
        with transaction.atomic():
            for view, values in (
                (GENERAL, general_values),
                (SPECIALTY, [asdict(row) for row in specialties]),
            ):
                changed = publish(
                    month, view, values, source, revision=bool(revision)
                )
                status = "publicado" if changed else "se conservó"
                self.stdout.write(f"{month} {view}: {status}")
        if path := options["csv"]:
            with path.open("w", encoding="utf-8-sig", newline="") as file:
                writer = csv.writer(file)
                writer.writerow(
                    [
                        "Empleado",
                        "Rol",
                        "Horas estimadas",
                        "AER facturable",
                        "AER no facturable",
                        "Horas variables facturables",
                        "Saldo",
                        "Fechas de registros válidos",
                    ]
                )
                for row in employee_detail(month, gse, general):
                    writer.writerow(
                        [
                            *row[:2],
                            *(round(value, 6) for value in row[2:7]),
                            row[7],
                        ]
                    )
        self.stdout.write(
            f"{general.resources} personas · "
            f"{general.capacity:,.2f} h estimadas · "
            f"{general.fixed_hours:,.2f} h AER · "
            f"{general.variable_hours:,.2f} h variables · "
            f"{general.free_hours:,.2f} h libres · "
            f"{general.global_percent:.2f}%"
        )
