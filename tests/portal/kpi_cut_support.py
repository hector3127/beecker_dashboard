"""Deterministic local inventory for independent KPI cut/year tests."""

from datetime import UTC, datetime


def stub_inventory(monkeypatch):
    from apps.portal.services.kpi_inventory_history import load_kpi_history

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
    monkeypatch.setattr(
        "apps.portal.services.kpi_inventory_history.load_inventory_eva", load
    )
    monkeypatch.setattr("apps.portal.views.load_kpi_history", load_kpi_history)
    return load
