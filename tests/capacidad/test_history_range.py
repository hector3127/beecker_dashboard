"""El rango de un proyecto no-MPB sale del Histórico antes que de Azure."""

from apps.capacidad.services.project_range import resolve_project_range


def _azure_must_not_be_used():
    raise AssertionError("Azure no debe consultarse si el Histórico responde")


def test_history_range_wins_over_azure():
    result = resolve_project_range(
        "IXB.010",
        "",
        False,
        lambda: {},
        _azure_must_not_be_used,
        lambda project: ("2026-03-02", "2026-06-30"),
    )

    assert result["ok"] is True
    assert (result["inicio"], result["fin"]) == ("2026-03-02", "2026-06-30")
    assert result["fuente"] == "Histórico"


def test_missing_history_falls_back_to_azure():
    class Azure:
        def resolve_project(self, project_id):
            return ""

        def list_iterations(self, azure_project, force_refresh):
            return []

    result = resolve_project_range(
        "IXB.010", "", False, lambda: {}, Azure, lambda project: None
    )

    assert result["ok"] is False
    assert "Team Project" in result["error"]
