"""Import the monthly report explicitly supplied by the user on 29/10/2026."""

from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.datastore.models import DmKpiMetric, DmKpiObservation, DmKpiPeriod
from apps.portal.services.kpi_dm_store import closing_day
from apps.portal.services.slugs import build_slug

MANAGERS = (
    "Brandon Daniel Sotelo Moreno",
    "Alberto Carlos Rodriguez Veloz",
    "Jose Patricio Ochoa Garza",
    "Enrique Yael Badillo Gutiérrez",
    "Lea Dayana Julian Figueroa",
    "Miguel Angel Policarpo Bacilio",
)
# Each position is a DM above: (TP, displayed T, displayed C within budget).
# None is an empty cell. Column '12' is an aggregate, not a month.
MONTHS = (
    (
        (8, 25, 63),
        (4, 100, 100),
        (5, 0, 40),
        (1, 0, 100),
        (1, 0, 100),
        (1, 100, 100),
    ),
    (
        (6, 17, 33),
        (5, 0, 60),
        (3, 0, 0),
        (3, 67, 67),
        (2, 100, 100),
        (1, 0, 100),
    ),
    ((4, 0, 75), (4, 0, 25), (3, 0, 33), (4, 0, 25), (2, 50, 50), None),
    ((4, 0, 75), (4, 0, 25), (3, 0, 33), (4, 0, 25), (2, 50, 50), None),
    ((4, 0, 75), (4, 0, 25), (3, 0, 33), (4, 0, 25), None, None),
    ((3, 100, 0), (4, 100, 50), (2, 100, 0), (3, 67, 33), None, None),
    ((4, 100, 50), (3, 100, 33), (2, 100, 50), (3, 67, 33), None, None),
    ((2, 100, 100), (3, 33, 33), (3, 67, 67), (2, 0, 0), None, None),
    ((2, 100, 100), (5, 40, 40), (2, 50, 50), None, None, None),
)
ORIGIN = "user_report_20261029"


def unique_count(total, displayed):
    """Accept only a unique integer compatible with the rounded percentage."""
    candidates = [
        count
        for count in range(total + 1)
        if abs(Decimal(100 * count) / total - displayed) <= Decimal("0.5")
    ]
    if len(candidates) != 1:
        raise ValueError(f"Porcentaje ambiguo: {total=}, {displayed=}")
    return candidates[0]


class Command(BaseCommand):
    """Import approved historical monthly rows, preserving existing periods."""

    help = "Carga enero–septiembre 2026 sin sobrescribir periodos existentes."

    @transaction.atomic
    def handle(self, *args, **options):
        """Validate and persist the complete report in one transaction."""
        created = 0
        for number, values in enumerate(MONTHS, 1):
            month = date(2026, number, 1)
            existing = DmKpiPeriod.objects.filter(month=month).first()
            if existing:
                if (
                    existing.latest_observation
                    and existing.latest_observation.origin == ORIGIN
                ):
                    continue
                raise CommandError(
                    f"Ya existe {month:%Y-%m}; no se sobrescribe."
                )
            cut = closing_day(month)
            period = DmKpiPeriod.objects.create(
                month=month,
                closing_day=cut,
                status="closed",
                closed_at=timezone.now(),
            )
            evidence = [
                {
                    "manager": name,
                    "tp": cell[0],
                    "t": cell[1],
                    "c_within_budget": cell[2],
                }
                for name, cell in zip(MANAGERS, values, strict=True)
                if cell
            ]
            observation = DmKpiObservation.objects.create(
                period=period,
                cut=cut,
                source_observed_at=timezone.now(),
                origin=ORIGIN,
                issues=[
                    {
                        "source": "codex-clipboard-"
                        "140f2b84-a386-46e4-80d1-be774a3d64b2.png",
                        "rows": evidence,
                        "note": "C de origen es cumplimiento; convertido a "
                        "sobrecosto. Conteos únicos compatibles con redondeo. "
                        "Corte por regla lunes–jueves; fecha original "
                        "del reporte no indicada.",
                        "reported_total": 19
                        if number in (1, 2)
                        else sum(c[0] for c in values if c),
                    }
                ],
            )
            for name, cell in zip(MANAGERS, values, strict=True):
                if cell is None:
                    continue
                tp, t, c = cell
                good_t, good_c = unique_count(tp, t), unique_count(tp, c)
                DmKpiMetric.objects.create(
                    observation=observation,
                    manager=name,
                    slug=build_slug(name),
                    total=tp,
                    on_time=good_t,
                    late=tp - good_t,
                    over_budget=tp - good_c,
                )
                created += 1
            period.latest_observation = observation
            period.save()
        self.stdout.write(
            f"Histórico importado: {created} filas DM; octubre sin cambios."
        )
