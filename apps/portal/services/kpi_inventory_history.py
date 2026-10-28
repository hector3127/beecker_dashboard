"""Monthly DM compliance from the same committed provider cuts as EVA 1."""

from dataclasses import replace

from django.utils import timezone

from apps.portal.services.eva_inventory_view import load_inventory_eva
from apps.portal.services.kpi_eva import build_eva_history, monthly_cuts
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
            replace(m, observed=observed[cut]["extraction"] is not None)
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
            "Sin cortes Azure/Clockify observados en: "
            + ", ".join(missing)
            + ". No se reconstruyen con el estado actual ni con Sheets."
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
    return KpiHistoryLoad(history, notice=notice)
