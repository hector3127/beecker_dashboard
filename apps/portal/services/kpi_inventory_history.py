"""Monthly DM compliance from the same committed provider cuts as EVA 1."""

from dataclasses import replace
from datetime import date

from django.utils import timezone

from apps.portal.schemas import KpiCut
from apps.portal.services.eva_inventory_view import load_inventory_eva
from apps.portal.services.eva_monthly_closes import is_closed_period
from apps.portal.services.kpi_eva import (
    build_eva_history,
    eva_manager_view,
    monthly_cuts,
)
from apps.portal.services.kpi_history_loader import KpiHistoryLoad


def load_kpi_history(year: int | None = None) -> KpiHistoryLoad:
    """Read observed cuts, never reconstruct old Summary from today's data."""
    now = timezone.localtime().replace(tzinfo=None)
    chosen = year or now.year
    cuts = monthly_cuts(chosen, now.date())
    if not cuts:
        return KpiHistoryLoad(
            None, "Aún no hay un corte de lunes a jueves en el periodo."
        )
    observed = {cut: load_inventory_eva(cut) for _, cut, _ in cuts}
    missing = [
        cut.isoformat()
        for cut, data in observed.items()
        if data["extraction"] is None
    ]
    history = build_eva_history(
        chosen, now, lambda cut: observed[cut]["projected_rows"]
    )
    history = replace(
        history,
        months=tuple(
            replace(
                m,
                observed=observed[cut]["extraction"] is not None,
                partial=False if is_closed_period(cut) else m.partial,
            )
            for m, (_, cut, _) in zip(history.months, cuts, strict=True)
        ),
    )
    by_day = {month.cut_label: month.observed for month in history.months}
    history = replace(
        history,
        quarters=tuple(
            replace(quarter, observed=by_day[quarter.cut_label])
            for quarter in history.quarters
        ),
    )
    notice = ""
    if missing:
        notice = (
            "Cierres mensuales pendientes de validar/cargar: "
            + ", ".join(missing)
            + ". No se recalculan con el Azure actual."
        )
    if any(
        data["error"]
        for data in observed.values()
        if data["extraction"] is not None
    ):
        notice += (
            " Hay incidencias de origen. TP cuenta servicios confirmados; "
            "los indicadores no verificables quedan pendientes."
        )
    existing = {m.key for m in history.months}
    full_year = monthly_cuts(chosen, date(chosen, 12, 31))
    history = replace(
        history,
        months=history.months
        + tuple(
            KpiCut(
                key,
                (
                    "Ene",
                    "Feb",
                    "Mar",
                    "Abr",
                    "May",
                    "Jun",
                    "Jul",
                    "Ago",
                    "Sep",
                    "Oct",
                    "Nov",
                    "Dic",
                )[int(key[5:7]) - 1],
                cut.strftime("%d/%m/%Y"),
                eva_manager_view([]),
                False,
                False,
            )
            for key, cut, _ in full_year
            if key not in existing
        ),
    )
    return KpiHistoryLoad(history, notice=notice)
