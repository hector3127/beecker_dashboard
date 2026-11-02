"""Financial bands fall back by month and person, never into the future."""

from datetime import date
from unittest.mock import Mock, patch

from apps.portal.services.revenue_costs import (
    prepare_cost_context,
    resolve_person_band,
)


def test_missing_current_month_uses_latest_previous_band():
    assert resolve_person_band(
        ["B1", "B2"],
        ["septiembre", "octubre"],
        {"B1": 10, "B2": 20},
        date(2026, 11, 2),
    ) == ("B2", "octubre")


def test_empty_or_departed_month_uses_persons_previous_band():
    for latest in ("", "Baja", "UNKNOWN"):
        assert resolve_person_band(
            ["B1", latest, "B3"],
            ["septiembre", "octubre", "diciembre"],
            {"B1": 10, "B3": 30},
            date(2026, 11, 2),
        ) == ("B1", "septiembre")


def test_current_band_has_priority_and_future_only_is_missing():
    assert resolve_person_band(
        ["B2", "B1"],
        ["noviembre", "octubre"],
        {"B1": 10, "B2": 20},
        date(2026, 11, 2),
    ) == ("B2", "noviembre")
    assert resolve_person_band(
        ["B2"],
        ["diciembre"],
        {"B2": 20},
        date(2026, 11, 2),
    ) == ("", "Sin banda vigente historica")


def test_context_accepts_roster_without_current_month():
    reader = Mock()
    reader.read_values.return_value = [
        ["band", "", "", "rate"],
        ["B1", "", "", 10],
    ]
    roster = Mock(headers=["nombre", "octubre"], data_rows=[["Ana", "B1"]])
    with (
        patch(
            "apps.portal.services.revenue_costs.read_roster_sheet",
            return_value=roster,
        ),
        patch(
            "apps.portal.services.revenue_costs.timezone.localdate",
            return_value=date(2026, 11, 2),
        ),
    ):
        result = prepare_cost_context(reader, ids=[])
    assert result.bands["ana"] == ("B1", "octubre")
