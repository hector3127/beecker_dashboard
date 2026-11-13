"""Datos iniciales aprobados; nunca reconstruye ni reemplaza cierres locales."""

import json
from datetime import date
from pathlib import Path

from django.db import transaction
from django.utils.dateparse import parse_datetime

from apps.datastore.models import (
    DmKpiMetric,
    DmKpiObservation,
    DmKpiPeriod,
    FacturabilityClose,
    SheetSnapshot,
)
from apps.portal.services.capacity_reference import HEADERS, REFERENCE_SHEET

DATA = Path(__file__).resolve().parents[1] / "data" / "approved_history.json"


@transaction.atomic
def install_approved_history():
    """Completa meses ausentes y conserva revisiones y ajustes existentes."""
    data = json.loads(DATA.read_text(encoding="utf-8"))
    counts = {"facturability": 0, "kpi_dm": 0, "capacity": 0}
    existing = set(FacturabilityClose.objects.values_list("month", "view"))
    for row in data["facturability"]:
        month = date.fromisoformat(row["month"])
        if (month, row["view"]) not in existing:
            FacturabilityClose.objects.create(**{**row, "month": month})
            counts["facturability"] += 1
    for row in data["kpi_dm"]:
        month = date.fromisoformat(row["month"])
        if DmKpiPeriod.objects.filter(month=month).exists():
            continue
        period = DmKpiPeriod.objects.create(
            month=month,
            closing_day=row["closing_day"],
            status="closed",
            closed_at=parse_datetime(row["closed_at"]),
        )
        observation = DmKpiObservation.objects.create(
            period=period,
            cut=row["cut"],
            origin=row["origin"],
            source_observed_at=parse_datetime(row["source_observed_at"]),
        )
        DmKpiMetric.objects.bulk_create(
            [
                DmKpiMetric(observation=observation, **metric)
                for metric in row["metrics"]
            ]
        )
        period.latest_observation = observation
        period.save(update_fields=["latest_observation"])
        counts["kpi_dm"] += 1
    snapshot = (
        SheetSnapshot.objects.select_for_update()
        .filter(
            name=REFERENCE_SHEET,
        )
        .first()
    )
    previous = snapshot.rows if snapshot else [HEADERS]
    if previous and previous[0] != HEADERS:
        raise ValueError("Encabezado de capacidad histórica incompatible.")
    covered = {row[0] for row in previous[1:]}
    added = [r for r in data["capacity"]["rows"][1:] if r[0] not in covered]
    if added:
        rows = [HEADERS, *previous[1:], *added]
        SheetSnapshot.objects.update_or_create(
            name=REFERENCE_SHEET,
            defaults={
                "rows": rows,
                "row_count": len(rows),
                "synced_at": snapshot.synced_at
                if snapshot
                else parse_datetime(data["capacity"]["synced_at"]),
            },
        )
        counts["capacity"] = len(added)
    return counts
