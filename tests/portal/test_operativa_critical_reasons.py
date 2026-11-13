"""Los críticos exponen el motivo de su clasificación existente."""

from types import SimpleNamespace as N

import pytest

from apps.portal.services.operational_sources import eva_projects


@pytest.mark.parametrize(
    ("days", "burn", "reasons"),
    [
        (10, 110, ["Consumo superior"]),
        (-3, 50, ["vencida hace 3 días"]),
        (-3, 110, ["Consumo superior", "vencida hace 3 días"]),
    ],
)
def test_critical_reasons(days, burn, reasons):
    project = N(
        project_id="AER.TEST.001",
        name="Prueba",
        manager="DM",
        service="AER",
        budget=100,
        burn=burn,
        etc=100 - burn,
        progress=burn,
        end="",
        renewal_days=days,
    )
    rows = eva_projects(N(view=N(projects=[project])), N(view=N(projects=[])))
    assert rows[0].health == "Crítica"
    assert all(reason in rows[0].health_reason for reason in reasons)
