"""La fuente del portafolio calcula indicadores sin escribir nada."""

import copy

from apps.portal.constants import NO_DELIVERY_MANAGER
from apps.portal.services.portfolio_source import build_project_views
from core.time_entries.models import TimeEntryBatch
from tests.dashboard.sample_data import NOW, SHEETS, TIME_ENTRIES
from tests.fakes import InMemorySheetRepository, StaticTimeEntryProvider


def load_views():
    repository = InMemorySheetRepository(copy.deepcopy(SHEETS))
    provider = StaticTimeEntryProvider(TimeEntryBatch(entries=TIME_ENTRIES))

    return build_project_views(repository, provider, NOW), repository


def test_builds_one_view_per_project():
    views, _ = load_views()

    assert [item.project_id for item in views] == [
        "P-1",
        "P-2",
        "P-3",
        "P-4",
        "P-5",
    ]


def test_maps_status_category_service_and_manager():
    views, _ = load_views()
    by_id = {item.project_id: item for item in views}

    assert by_id["P-1"].status_category == "Activo"
    assert by_id["P-1"].service == "AER"
    assert by_id["P-1"].delivery_manager == "Laura"
    assert by_id["P-2"].delivery_manager == "Mario"
    assert by_id["P-5"].status_category == "En Pausa"
    assert by_id["P-4"].status_category == "Cerrado"
    assert by_id["P-3"].delivery_manager == NO_DELIVERY_MANAGER


def test_keeps_hours_from_the_dashboard_metrics():
    views, _ = load_views()
    by_id = {item.project_id: item for item in views}

    assert by_id["P-1"].budget_hours == 100
    assert by_id["P-1"].etc_hours == 100 - by_id["P-1"].burn_hours


def test_never_writes_to_sheets():
    _, repository = load_views()

    assert repository.appended_rows == []
    assert repository.replaced_rows == []
