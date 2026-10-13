"""T (desviacion promedio en dias) y C (avance promedio)."""

from apps.portal.services.eva1 import build_eva1_view
from apps.portal.services.eva2 import build_eva2_view
from apps.portal.services.manager_detail import build_manager_detail
from apps.portal.services.portfolio_summary import (
    summarize_delivery_managers,
)
from apps.portal.services.time_cost import (
    average,
    build_time_cost,
    summarize_time_cost,
)
from tests.portal.builders import make_project
from tests.portal.test_eva1 import sample_rows
from tests.portal.test_eva2 import make_row


def test_average_ignores_missing_values():
    assert average([1, 2, None, 4]) == 2.3
    assert average([]) is None
    assert average([None]) is None
    assert average([-3, 1]) == -1.0


def test_build_time_cost():
    result = build_time_cost([2, -4, None], [50, 100])

    assert result.time_days == -1.0
    assert result.cost_percent == 75.0


def test_portfolio_time_cost_uses_only_in_progress():
    projects = [
        make_project(delay_days=4, progress_percent=40),
        make_project(delay_days=0, progress_percent=80),
        make_project(
            delay_days=30,
            progress_percent=10,
            status_category="En Pausa",
        ),
    ]

    result = summarize_time_cost(projects)

    assert result.time_days == 2.0
    assert result.cost_percent == 60.0
    assert summarize_time_cost([]).time_days is None


def test_manager_cards_and_detail_have_time_cost():
    projects = [
        make_project(delay_days=6, progress_percent=30),
        make_project(delay_days=0, progress_percent=90),
        make_project(delivery_manager="Ana", status_category="En Pausa"),
    ]

    cards = {card.name: card for card in summarize_delivery_managers(projects)}
    detail = build_manager_detail("Laura Vega", projects[:2])

    assert cards["Laura Vega"].time_cost.time_days == 3.0
    assert cards["Laura Vega"].time_cost.cost_percent == 60.0
    assert cards["Ana"].time_cost.cost_percent is None
    assert detail.time_cost.time_days == 3.0


def test_eva2_time_cost_uses_deviation_and_progress():
    view = build_eva2_view(
        [
            make_row(desviacionDias=-10, avance=50),
            make_row(desviacionDias=4, avance=100),
            make_row(desviacionDias=None, avance=75),
        ],
    )

    assert view.time_cost.time_days == -3.0
    assert view.time_cost.cost_percent == 75.0
    assert build_eva2_view([]).time_cost.time_days is None


def test_eva1_cost_is_the_average_progress():
    assert build_eva1_view(sample_rows()).cost_percent == 72.5
    assert build_eva1_view([]).cost_percent is None
