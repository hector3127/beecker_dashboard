"""Top de cuentas, KPIs de Delivery Managers y tarjetas EVA."""

from django.core.cache import cache

from apps.portal.constants import EVA2_CACHE_KEY
from apps.portal.services.account_ranking import rank_accounts
from apps.portal.services.eva1 import build_eva1_view
from apps.portal.services.eva_loader import (
    Eva1Load,
    build_eva1_card,
    peek_eva2_card,
)
from apps.portal.services.kpis_dm import build_kpi_view
from tests.portal.builders import make_project
from tests.portal.test_eva1 import sample_rows
from tests.portal.test_eva2 import make_row


def portfolio():
    return [
        make_project(project_id="1", client="ACME"),
        make_project(project_id="2", client="ACME"),
        make_project(project_id="3", client="Globex"),
        make_project(project_id="4", client="Sur", health="Crítica"),
        make_project(project_id="5", client="Sur"),
        make_project(project_id="6", client="Norte", health="En Riesgo"),
        make_project(
            project_id="7",
            client="Pausada",
            status_category="En Pausa",
        ),
        make_project(project_id="8", client=""),
        make_project(project_id="9", client="Delta"),
        make_project(project_id="10", client="Omega"),
    ]


def test_rank_accounts_healthy_and_unhealthy():
    healthy, unhealthy = rank_accounts(portfolio())

    assert [item.name for item in healthy] == ["ACME", "Delta", "Globex"]
    assert healthy[0].in_progress == 2
    assert healthy[0].on_time_percent == 100
    assert healthy[0].slug == "acme"
    assert [item.name for item in unhealthy] == ["Sur", "Norte"]
    assert unhealthy[0].health.critical == 1
    assert unhealthy[0].on_time_percent == 50


def test_rank_accounts_empty():
    assert rank_accounts([]) == ((), ())


def test_kpi_view_rows_totals_best_and_worst():
    projects = [
        make_project(project_id="1", delay_days=2, progress_percent=40),
        make_project(project_id="2", health="Crítica", progress_percent=80),
        make_project(project_id="3", delivery_manager="Ana", delay_days=6),
        make_project(
            project_id="4",
            delivery_manager="Pausa",
            status_category="En Pausa",
        ),
    ]

    view = build_kpi_view(projects)

    assert [row.name for row in view.rows] == ["Laura Vega", "Ana"]
    laura = view.rows[0]
    assert (laura.total, laura.on_time_percent) == (2, 50)
    assert laura.time_cost.time_days == 1.0
    assert laura.time_cost.cost_percent == 60.0
    assert view.totals.total == 3
    assert view.totals.health.critical == 1
    assert view.totals.time_cost.time_days == 2.7
    assert view.best.name == "Ana"
    assert view.worst.name == "Laura Vega"


def test_kpi_view_with_one_or_no_manager():
    single = build_kpi_view([make_project()])
    empty = build_kpi_view([])

    assert single.best.name == "Laura Vega"
    assert single.worst is None
    assert empty.rows == ()
    assert empty.best is None
    assert empty.totals.total == 0


def test_eva1_card():
    ok = build_eva1_card(
        Eva1Load(view=build_eva1_view(sample_rows()), error="")
    )
    failed = build_eva1_card(Eva1Load(view=build_eva1_view([]), error="x"))

    assert ok.available is True
    assert ok.total_projects == 3
    assert ok.time_cost.cost_percent == 72.5
    assert ok.time_cost.time_days is None
    assert failed.available is False


def test_eva2_card_only_uses_the_cache():
    cache.delete(EVA2_CACHE_KEY)

    assert peek_eva2_card().available is False

    cache.set(
        EVA2_CACHE_KEY,
        {"ok": True, "filas": [make_row(desviacionDias=-4, avance=60)]},
    )
    card = peek_eva2_card()

    assert card.available is True
    assert card.total_projects == 1
    assert card.time_cost.time_days == -4.0
    assert card.time_cost.cost_percent == 60.0
    cache.delete(EVA2_CACHE_KEY)
