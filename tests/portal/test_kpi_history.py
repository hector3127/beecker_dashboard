from datetime import date, datetime

from apps.dashboard.schemas.records import ProjectRecord
from apps.portal.services.kpi_history import (
    HistorySources,
    build_kpi_history,
    build_matrix,
    chart_series,
    month_cuts,
)
from core.time_entries.models import TimeEntry

NOW = datetime(2026, 10, 13, 12, 0)


def project(project_id, status, start, end, budget=100.0):
    return ProjectRecord(
        project_id=project_id,
        display_name=project_id,
        client="ACME",
        status=status,
        service="AER",
        budget_hours=budget,
        start_date=start,
        end_date=end,
    )


def entry(project_id, day, hours):
    return TimeEntry(
        entry_id=f"{project_id}-{day}",
        project_id=project_id,
        resource_name="Ana",
        entry_date=day,
        duration_hours=hours,
        is_billable=True,
        costing_rate=0.0,
    )


def sources():
    return HistorySources(
        projects=[
            project(
                "A",
                "Development",
                datetime(2026, 1, 1),
                datetime(2026, 12, 31),
            ),
            project(
                "B",
                "Cancelado",
                datetime(2026, 1, 1),
                datetime(2026, 3, 15),
            ),
            project(
                "C",
                "Suspendido",
                datetime(2026, 1, 1),
                datetime(2026, 12, 31),
            ),
            project(
                "D",
                "Development",
                datetime(2026, 6, 1),
                datetime(2026, 12, 31),
            ),
        ],
        entries=[
            entry("A", datetime(2026, 2, 10), 10.0),
            entry("A", datetime(2026, 9, 10), 30.0),
            entry("B", datetime(2026, 2, 12), 50.0),
        ],
        risks=[],
        managers={"A": "Ana", "B": "Ana", "C": "Ana", "D": "Beto"},
    )


def test_month_cuts_end_at_month_end_and_today():
    cuts = month_cuts(2026, date(2026, 3, 10))

    assert cuts == [
        ("2026-01", date(2026, 1, 31)),
        ("2026-02", date(2026, 2, 28)),
        ("2026-03", date(2026, 3, 10)),
    ]


def test_past_year_has_twelve_cuts_ending_each_month():
    cuts = month_cuts(2025, date(2026, 10, 13))

    assert len(cuts) == 12
    assert cuts[1] == ("2025-02", date(2025, 2, 28))
    assert cuts[-1] == ("2025-12", date(2025, 12, 31))
    history = build_kpi_history(sources(), NOW, 2025)
    assert [cut.label for cut in history.quarters] == ["T1", "T2", "T3", "T4"]
    assert not any(cut.partial for cut in history.months)


def test_each_month_uses_the_hours_until_its_cut():
    history = build_kpi_history(sources(), NOW, 2026)
    february = history.months[1].view.rows[0]

    assert [cut.label for cut in history.months][:2] == ["Ene", "Feb"]
    assert february.name == "Ana"
    assert february.total == 2
    assert february.time_cost.cost_percent == 30.0
    assert history.months[8].view.rows[0].time_cost.cost_percent == 40.0


def test_projects_enter_only_when_they_were_running():
    history = build_kpi_history(sources(), NOW, 2026)
    totals = [cut.view.totals.total for cut in history.months]

    assert totals[1] == 2  # A y B; C esta en pausa hoy
    assert totals[3] == 1  # B ya cerro el 15 de marzo
    assert totals[5] == 2  # D inicia en junio
    assert history.months[-1].partial is True
    assert history.months[-1].label == "Oct"


def test_quarters_take_the_last_month_cut():
    history = build_kpi_history(sources(), NOW, 2026)

    assert [cut.label for cut in history.quarters] == ["T1", "T2", "T3", "T4"]
    assert history.quarters[2].view == history.months[8].view
    assert history.quarters[3].partial is True


def test_matrix_has_one_row_per_manager_and_blank_cells():
    history = build_kpi_history(sources(), NOW, 2026)
    matrix = build_matrix(history.months, history.managers)
    names = [row.name for row in matrix.rows]
    beto = matrix.rows[names.index("Beto")]

    assert matrix.headers[0] == "Ene"
    assert matrix.headers[-1] == "Oct*"
    assert beto.cells[0] is None
    assert beto.cells[5] is not None
    assert len(matrix.totals) == len(matrix.headers)


def test_chart_series_limits_managers():
    history = build_kpi_history(sources(), NOW, 2026)
    matrix = build_matrix(history.months, history.managers)
    chart = chart_series(matrix, 1)

    assert len(chart["series"]) == 1
    assert chart["labels"][0] == "Ene"
