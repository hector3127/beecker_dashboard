"""Quarterly averages preserve the GSE aggregation, not month-end values."""

from dataclasses import replace

from apps.portal.services.kpi_history import build_kpi_history
from apps.portal.services.kpi_quarterly import build_quarter_averages
from tests.portal.test_kpi_history import NOW, sources


def test_quarter_is_monthly_mean_and_keeps_fractional_project_counts():
    history = build_kpi_history(sources(), NOW, 2026)
    cuts = list(history.months[:3])
    for index, count in enumerate([8, 6, 4]):
        cut = cuts[index]
        row = replace(cut.view.rows[0], total=count)
        cuts[index] = replace(
            cut, view=replace(cut.view, rows=(row,), totals=row)
        )
    result = build_quarter_averages(cuts, ((row.name, row.slug),))
    assert result.headers == ("T1",)
    assert result.rows[0].cells[0].total == 6
    assert result.totals[0].total == 6
    assert result.totals[0].total != cuts[-1].view.totals.total


def test_missing_months_are_not_zero_and_current_quarter_is_marked():
    history = build_kpi_history(sources(), NOW, 2026)
    cuts = list(history.months[:3])
    manager = cuts[0].view.rows[0]
    cuts[1] = replace(cuts[1], view=replace(cuts[1].view, rows=()))
    result = build_quarter_averages(cuts, ((manager.name, manager.slug),))
    expected = (cuts[0].view.rows[0].total + cuts[2].view.rows[0].total) / 2
    assert result.rows[0].cells[0].total == expected
    assert build_quarter_averages(
        history.months[-1:], history.managers
    ).headers == ("T4*",)
    assert build_quarter_averages([], ()).headers == ()
