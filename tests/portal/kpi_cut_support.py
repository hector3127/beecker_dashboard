"""Deterministic local inventory for independent KPI cut/year tests."""

from datetime import UTC, datetime


def stub_inventory(monkeypatch):
    from datetime import date
    from types import SimpleNamespace

    from django.utils import timezone

    from apps.portal.schemas import KpiCut, KpiHistory
    from apps.portal.services.kpi_dm_store import StoredKpiCut
    from apps.portal.services.kpi_eva import (
        build_eva_history,
        eva_manager_view,
        monthly_cuts,
    )
    from apps.portal.services.kpi_history import _managers
    from apps.portal.services.kpi_history_loader import KpiHistoryLoad

    def load(cut):
        rows = [
            {
                "idProyecto": "A",
                "deliveryManager": "Ana",
                "desviacionDias": -1,
                "budget": 100,
                "avance": 150,
            },
            {
                "idProyecto": "B",
                "deliveryManager": "Beto",
                "desviacionDias": 0,
                "budget": 100,
                "avance": 100,
            },
        ]
        if cut.month >= 3:
            rows.append(
                {
                    "idProyecto": "C",
                    "deliveryManager": "Ana",
                    "desviacionDias": 1,
                    "budget": 100,
                    "avance": 0,
                    "hours_pending": True,
                }
            )
        return {"projected_rows": rows, "extraction": object(), "error": ""}

    monkeypatch.setattr(
        "django.utils.timezone.now",
        lambda: datetime(2026, 10, 28, 18, tzinfo=UTC),
    )
    monkeypatch.setattr(
        "apps.portal.services.eva_inventory_view.load_inventory_eva", load
    )

    def load_history(year=None):
        year = year or 2026
        history = build_eva_history(
            year,
            datetime(2026, 10, 28),
            lambda cut: load(cut)["projected_rows"],
        )
        existing = {month.key for month in history.months}
        missing = tuple(
            KpiCut(
                key,
                [
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
                ][int(key[5:7]) - 1],
                cut.strftime("%d/%m/%Y"),
                eva_manager_view([]),
                False,
                False,
            )
            for key, cut, _ in monthly_cuts(year, date(year, 12, 31))
            if key not in existing
        )
        months = history.months + missing
        return KpiHistoryLoad(KpiHistory(months, (), _managers(months)))

    def load_cut(cut):
        return StoredKpiCut(
            eva_manager_view(load(cut)["projected_rows"]),
            SimpleNamespace(period=SimpleNamespace(status="open")),
        )

    monkeypatch.setattr(
        "apps.portal.services.kpi_dm_store.latest_kpi_cut",
        lambda: min(timezone.localdate(), date(2026, 10, 28)),
    )
    monkeypatch.setattr(
        "apps.portal.services.kpi_dm_store.load_kpi_cut", load_cut
    )
    monkeypatch.setattr("apps.portal.views.load_kpi_history", load_history)
    return load
