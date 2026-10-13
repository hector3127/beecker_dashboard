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


def test_manager_lookup_prefers_mpb_then_history():
    from apps.capacidad.services.mpb_projects import MpbProject  # noqa: PLC0415
    from apps.portal.services.portfolio_source import (  # noqa: PLC0415
        ManagerLookup,
    )

    mpb = {
        "aer awn 001": MpbProject(
            "AER.AWN.001", "aer", "", "", "Soporte", "Ana"
        ),
        "tym x 001": MpbProject("TYM.X.001", "tym", "", "", "X", " "),
    }
    history = {"AMK.008": "Luis", "TYM.X.001": "Eva", "IXB.002": "Pedro"}
    lookup = ManagerLookup(mpb, history)

    assert lookup.find("AER.AWN.001") == "Ana"
    assert lookup.find("TYM.X.001") == "Eva"
    assert lookup.find("AMK.008_S4") == "Luis"
    assert lookup.find("ixb.002") == "Pedro"
    assert lookup.find("NADA") == ""
    assert lookup.as_mapping(["AER.AWN.001", "NADA"]) == {"AER.AWN.001": "Ana"}
