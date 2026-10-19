"""DM investment is grouped from the shared cached project totals."""

from types import SimpleNamespace

from apps.portal.services.portfolio_summary import summarize_delivery_managers
from apps.portal.templatetags.manager_investment import manager_investment
from tests.portal.builders import make_project


def test_manager_projects_are_unique_and_belong_to_that_manager():
    projects = [
        make_project(project_id="IXB.1", delivery_manager="Ana"),
        make_project(project_id="IXB.2", delivery_manager="Ana"),
        make_project(project_id="IXB.3", delivery_manager="Beto"),
    ]
    ana = next(
        dm for dm in summarize_delivery_managers(projects) if dm.name == "Ana"
    )
    assert ana.project_ids == ("IXB.1", "IXB.2")
    result = manager_investment(
        ana,
        {
            "complete": True,
            "by_project": {
                "IXB.1": {"commercial": 2.5, "operational": 7},
                "IXB.2": {"commercial": 3, "operational": 0},
                "IXB.3": {"commercial": 100, "operational": 90},
            },
        },
    )
    assert result["ready"]
    assert (result["commercial"], result["operational"]) == (5.5, 7)


def test_missing_and_partial_investment_are_not_reported_as_zero():
    dm = SimpleNamespace(project_ids=("IXB.1",))
    for investment in (
        {},
        {"complete": True, "by_project": {}},
        {"complete": False, "by_project": {"IXB.1": {"commercial": 2}}},
    ):
        result = manager_investment(dm, investment)
        assert not result["ready"]
        assert result["commercial"] is None
        assert result["operational"] is None
    result = manager_investment(
        dm,
        {
            "complete": True,
            "by_project": {"IXB.1": {"commercial": 0, "operational": 0}},
        },
    )
    assert result["ready"]
    assert result["commercial"] == result["operational"] == 0


def test_dashboard_includes_aer_and_tym_without_loading_extra_consumption(
    monkeypatch,
):
    from unittest.mock import Mock

    from apps.portal.views import _operativa_investment

    projects = [
        SimpleNamespace(project_id=pid) for pid in ("IXB.1", "AER.2", "TYM.3")
    ]
    expected = {
        "complete": True,
        "by_project": {"TYM.3": {"commercial": 4, "operational": 9}},
    }
    tagged = Mock(return_value=expected)
    monkeypatch.setattr(
        "apps.portal.services.operational_sources.tagged_investment", tagged
    )
    ixb = SimpleNamespace(error="", view=SimpleNamespace(projects=projects[:1]))
    aer = SimpleNamespace(error="", view=SimpleNamespace(projects=projects[1:]))
    assert _operativa_investment(ixb, aer) == expected
    tagged.assert_called_once_with(projects)
    dm = SimpleNamespace(project_ids=("TYM.3",))
    result = manager_investment(dm, expected)
    assert (result["commercial"], result["operational"]) == (4, 9)


def test_missing_mpb_population_does_not_claim_complete_investment(monkeypatch):
    from unittest.mock import Mock

    from apps.portal.views import _operativa_investment

    tagged = Mock()
    monkeypatch.setattr(
        "apps.portal.services.operational_sources.tagged_investment", tagged
    )
    result = _operativa_investment(
        SimpleNamespace(error="", view=SimpleNamespace(projects=[])),
        SimpleNamespace(error="MPB no disponible"),
    )
    assert not result["complete"]
    assert "MPB no disponible" in result["error"]
    tagged.assert_not_called()
